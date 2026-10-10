"""
core/latex_editor.py
Optional "preserve exact design" pipeline: takes YOUR resume's own LaTeX
source (exported from Overleaf), asks the AI to edit ONLY the visible text
(not formatting commands), then compiles it back to a PDF with pdflatex --
so the output looks exactly like your original template, just improved.

Requires a local LaTeX install (pdflatex on PATH). TinyTeX recommended --
see README.
"""

import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

COMMAND_PATTERN = re.compile(r"\\[a-zA-Z]+")
SECTION_HEADING_PATTERN = re.compile(r"\\section\*?\{([^}]*)\}")
ITEM_PATTERN = re.compile(r"\\item\s+(.*?)(?=\n\s*\\item|\n\s*\\end\{itemize\})", re.DOTALL)

# Which \section{...} headings are safe to rewrite content in. Anything not
# matching these (Education, Additional Training, Certifications, contact
# info, etc.) is left completely untouched by design -- those are facts, not
# prose, and shouldn't be paraphrased or risk fabrication.
BULLET_SECTION_KEYWORDS = ("experience", "work", "project", "employment")
PARAGRAPH_SECTION_KEYWORDS = ("summary", "profile", "objective")


@dataclass
class TexSegment:
    id: str
    text: str
    start: int
    end: int


def _section_spans(tex: str) -> list[tuple[str, int, int]]:
    """(heading_text_lowercased, content_start, content_end) for every
    \\section*{...} — content_end is the next heading's start, or EOF."""
    headings = list(SECTION_HEADING_PATTERN.finditer(tex))
    spans = []
    for i, m in enumerate(headings):
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(tex)
        spans.append((m.group(1).strip().lower(), start, end))
    return spans


def _heading_matches(heading: str, keywords) -> bool:
    """Word-start match, so 'work' matches 'Work Experience' but not 'Teamwork' or 'Networking'."""
    return any(re.search(r"\b" + re.escape(k), heading) for k in keywords)


def extract_segments(tex: str) -> list[TexSegment]:
    """Finds only the safe-to-rewrite prose: the summary paragraph and
    bullet points inside Experience/Project-like sections. Job titles,
    dates, company names, education, certifications, and contact info are
    never touched -- they're facts, not something to paraphrase."""
    segments = []
    bullet_n = 0
    for heading, start, end in _section_spans(tex):
        chunk = tex[start:end]
        if _heading_matches(heading, PARAGRAPH_SECTION_KEYWORDS):
            m = re.search(r"\S.*?(?=\n\s*\n|\Z)", chunk, re.DOTALL)
            if m:
                segments.append(TexSegment(
                    "summary", m.group(0).strip(), start + m.start(), start + m.end()))
        elif _heading_matches(heading, BULLET_SECTION_KEYWORDS):
            for m in ITEM_PATTERN.finditer(chunk):
                bullet_n += 1
                segments.append(TexSegment(
                    f"bullet_{bullet_n}", m.group(1).strip(),
                    start + m.start(1), start + m.end(1)))
    return segments


def _auto_escape(text: str) -> str:
    """Safety net on top of prompting: escape LaTeX special characters that
    aren't already escaped. An unescaped '%' silently truncates the rest of
    the line when compiled, so this matters."""
    return re.sub(r"(?<!\\)([%$&#_])", r"\\\1", text)


def apply_edits(tex: str, segments: list[TexSegment], edits: dict) -> str:
    """Reconstructs the tex with each segment's text replaced by its edit,
    working back-to-front so earlier character offsets stay valid."""
    for seg in sorted(segments, key=lambda s: s.start, reverse=True):
        if seg.id in edits and isinstance(edits[seg.id], str) and edits[seg.id].strip():
            new_text = _auto_escape(edits[seg.id].strip())
            tex = tex[:seg.start] + new_text + tex[seg.end:]
    return tex


def segments_to_json(segments: list[TexSegment]) -> str:
    return json.dumps([{"id": s.id, "text": s.text} for s in segments], indent=2)


def pdflatex_available() -> bool:
    return shutil.which("pdflatex") is not None


def structure_diff(original_tex: str, edited_tex: str) -> dict:
    """Best-effort check that the AI only changed text, not LaTeX structure:
    compares how many times each LaTeX command is used before vs. after."""
    orig = Counter(COMMAND_PATTERN.findall(original_tex))
    new = Counter(COMMAND_PATTERN.findall(edited_tex))
    changed = {c: (orig.get(c, 0), new.get(c, 0))
               for c in set(orig) | set(new) if orig.get(c, 0) != new.get(c, 0)}
    return {"structure_preserved": len(changed) == 0, "changed_commands": changed}


def compile_pdf(tex_source: str, output_pdf_path: str) -> str:
    if not pdflatex_available():
        raise RuntimeError(
            "pdflatex isn't installed (or not on PATH). Install a LaTeX "
            "distribution -- TinyTeX is the lightest option. See README."
        )
    with tempfile.TemporaryDirectory() as workdir:
        tex_path = Path(workdir) / "resume.tex"
        tex_path.write_text(tex_source, encoding="utf-8")
        result = None
        for _ in range(2):  # twice: settles spacing/refs, harmless if unneeded
            try:
                result = subprocess.run(
                    # No -halt-on-error: matches Overleaf's default behavior of
                    # recovering from non-fatal errors (e.g. a stray '#' in a
                    # \href URL) and still producing a PDF, rather than aborting.
                    ["pdflatex", "-interaction=nonstopmode",
                     "-output-directory", workdir, str(tex_path)],
                    cwd=workdir, capture_output=True, text=True, timeout=120,
                )
            except subprocess.TimeoutExpired:
                raise RuntimeError(
                    "pdflatex timed out. If this is your first compile, TinyTeX may be "
                    "downloading missing packages -- try once more.")
        produced = Path(workdir) / "resume.pdf"
        if not produced.exists() or produced.stat().st_size == 0:
            log_path = Path(workdir) / "resume.log"
            excerpt = ""
            if log_path.exists():
                lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                errors = [l for l in lines if l.startswith("!")]
                excerpt = "\n".join(errors[-10:]) or "\n".join(lines[-20:])
            raise RuntimeError(f"LaTeX compilation failed:\n{excerpt}")
        shutil.copy(produced, output_pdf_path)
        return output_pdf_path
