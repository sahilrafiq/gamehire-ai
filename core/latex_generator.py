"""
core/latex_generator.py
For PDF/DOCX/TXT input (no original .tex): builds a new LaTeX resume from
the parsed content, using ONLY packages that ship in a default TinyTeX
install (geometry, xcolor, hyperref, enumitem, titlesec -- no libertinus,
no fontawesome5), so it compiles everywhere without extra tlmgr installs.
"""

import re
from core.parser import parse_blocks
from core.ats import EMAIL_PATTERN, PHONE_PATTERN

PREAMBLE = r"""\documentclass[10pt,a4paper]{article}
\usepackage[a4paper,margin=0.75in]{geometry}
\usepackage[T1]{fontenc}
\usepackage{xcolor}
\usepackage[hidelinks]{hyperref}
\usepackage{enumitem}
\usepackage{titlesec}
\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{4pt}
\definecolor{accent}{HTML}{0F4C81}
\titleformat{\section}{\large\bfseries\color{accent}}{}{0em}{}[\titlerule]
\titlespacing*{\section}{0pt}{8pt}{4pt}
\setlist[itemize]{leftmargin=1.2em,itemsep=1pt,topsep=2pt,parsep=0pt}
\begin{document}
"""


def _esc(text: str) -> str:
    return re.sub(r"(?<!\\)([%$&#_])", r"\\\1", text)


def _split_header(text: str, blocks: list) -> tuple[dict, list]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    name = lines[0] if lines else "Resume"
    header = {"name": name}

    m = EMAIL_PATTERN.search(text)
    if m:
        header["email"] = m.group(0)
    m = PHONE_PATTERN.search(text)
    if m:
        header["phone"] = m.group(0).strip()
    m = re.search(r"linkedin\.com/\S+", text, re.IGNORECASE)
    if m:
        header["linkedin"] = m.group(0).rstrip(".,)")
    m = re.search(r"github\.com/\S+", text, re.IGNORECASE)
    if m:
        header["github"] = m.group(0).rstrip(".,)")

    body = []
    seen_name = False
    for b in blocks:
        if b.kind == "paragraph":
            if not seen_name and b.text.strip() == name:
                seen_name = True
                continue
            if (EMAIL_PATTERN.search(b.text) or PHONE_PATTERN.search(b.text)
                    or "linkedin.com" in b.text.lower() or "github.com" in b.text.lower()):
                continue
        body.append(b)
    return header, body


def generate_tex(resume_text: str) -> str:
    blocks = parse_blocks(resume_text)
    header, body = _split_header(resume_text, blocks)

    parts = [PREAMBLE, r"\begin{center}",
             r"{\LARGE \textbf{%s}}\\[4pt]" % _esc(header["name"])]

    bits = []
    if "email" in header:
        bits.append(r"\href{mailto:%s}{%s}" % (header["email"], _esc(header["email"])))
    if "phone" in header:
        bits.append(_esc(header["phone"]))
    if "linkedin" in header:
        bits.append(r"\href{https://%s}{%s}" % (header["linkedin"], _esc(header["linkedin"])))
    if "github" in header:
        bits.append(r"\href{https://%s}{%s}" % (header["github"], _esc(header["github"])))
    parts.append(r" \quad$\vert$\quad ".join(bits))
    parts.append(r"\end{center}\vspace{4pt}")

    in_items = False
    for b in body:
        if b.kind == "heading":
            if in_items:
                parts.append(r"\end{itemize}"); in_items = False
            parts.append(r"\section*{%s}" % _esc(b.text.title()))
        elif b.kind == "bullet":
            if not in_items:
                parts.append(r"\begin{itemize}"); in_items = True
            parts.append(r"\item %s" % _esc(b.text))
        else:
            if in_items:
                parts.append(r"\end{itemize}"); in_items = False
            parts.append(_esc(b.text) + r"\\")
    if in_items:
        parts.append(r"\end{itemize}")

    parts.append(r"\end{document}")
    return "\n".join(parts)
