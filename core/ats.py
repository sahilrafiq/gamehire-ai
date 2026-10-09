"""
core/ats.py
Rule-based ATS compatibility & keyword-match scorer. Deterministic and free
(no API calls). Works two ways:

  ats.score(resume_text)                     -> general ATS/best-practices score
  ats.score(resume_text, job_description)     -> general score + role-specific
                                                  keyword match score, combined

Pair with core.ai.general_resume_review() or core.ai.keyword_gap_analysis()
for a richer, AI-assisted read of the same resume.
"""

import re
from collections import Counter

STOPWORDS = set("""
a an the and or but if of to in on for with at by from as is are was were be
been being this that these those it its into over under than then so such
your you we our their his her they he she i not no yes will can may
""".split())

SECTION_HEADERS = ["experience", "education", "skills", "summary", "projects",
                    "certifications", "work history", "employment"]

# Common, ATS-favored resume action verbs. Not exhaustive -- used as a
# heuristic signal, not a strict whitelist.
ACTION_VERBS = set("""
achieved managed led built created developed implemented designed improved
increased reduced launched delivered coordinated analyzed automated optimized
spearheaded negotiated mentored trained executed streamlined generated
established founded directed organized authored produced resolved
accelerated architected engineered deployed scaled migrated refactored
drove grew cut saved reduced boosted expanded initiated pioneered
collaborated presented published researched tested debugged
""".split())

QUANT_PATTERN = re.compile(r"(\$\s?\d|\d+%|\d+x\b|\d+\+|\d+k\b|\d+m\b)", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_PATTERN = re.compile(r"(\+?\d[\d\-\s()]{8,}\d)")
PRONOUN_PATTERN = re.compile(r"\bI\b|\bmy\b|\bme\b", re.IGNORECASE)


def _tokenize(text: str) -> list[str]:
    raw = re.findall(r"[a-zA-Z][a-zA-Z+/#.]{1,}", text.lower())
    words = [w.strip(".") for w in raw]
    return [w for w in words if w and w not in STOPWORDS and len(w) > 2]


def _top_keywords(text: str, n: int = 30) -> list[str]:
    counts = Counter(_tokenize(text))
    return [w for w, _ in counts.most_common(n)]


def _bullets(resume_text: str) -> list[str]:
    return [l.strip()[2:].strip() for l in resume_text.splitlines()
            if l.strip().startswith(("- ", "• ", "* "))]


def _general_analysis(resume_text: str) -> dict:
    word_count = len(resume_text.split())
    length_ok = 350 <= word_count <= 900

    has_email = bool(EMAIL_PATTERN.search(resume_text))
    has_phone = bool(PHONE_PATTERN.search(resume_text))

    lowered = resume_text.lower()
    found_headers = [h for h in SECTION_HEADERS if h in lowered]

    bullets = _bullets(resume_text)
    has_bullets = len(bullets) >= 3
    if bullets:
        action_verb_hits = sum(
            1 for b in bullets if b.split()[0].lower().rstrip(",.") in ACTION_VERBS
            if b.split()
        )
        strong_action_verbs = (action_verb_hits / len(bullets)) >= 0.5
    else:
        strong_action_verbs = False

    has_quantified = bool(QUANT_PATTERN.search(resume_text))
    avoids_pronouns = not bool(PRONOUN_PATTERN.search(resume_text))

    checks = {
        "Contact info found (email)": has_email,
        "Contact info found (phone)": has_phone,
        "Reasonable length (350-900 words)": length_ok,
        "Has standard section headers": len(found_headers) >= 2,
        "Uses bullet points": has_bullets,
        "Bullets start with strong action verbs": strong_action_verbs,
        "Includes quantifiable achievements (numbers/%/$)": has_quantified,
        "Avoids first-person pronouns (I, my, me)": avoids_pronouns,
    }
    score = round(100 * sum(checks.values()) / len(checks))

    return {
        "score": score,
        "checks": checks,
        "word_count": word_count,
        "found_section_headers": found_headers,
    }


def _keyword_analysis(resume_text: str, job_description: str) -> dict:
    jd_keywords = _top_keywords(job_description, n=30)
    resume_words = set(_tokenize(resume_text))

    matched = [kw for kw in jd_keywords if kw in resume_words]
    missing = [kw for kw in jd_keywords if kw not in resume_words]
    score = round(100 * len(matched) / max(len(jd_keywords), 1))

    return {"score": score, "matched": matched, "missing": missing}


def score(resume_text: str, job_description: str | None = None) -> dict:
    """General ATS/best-practices score always included. If job_description
    is provided (non-empty), also scores keyword match against it and blends
    the two into an overall, role-specific score."""
    general = _general_analysis(resume_text)

    result = {
        "mode": "general",
        "general_score": general["score"],
        "general_checks": general["checks"],
        "word_count": general["word_count"],
        "found_section_headers": general["found_section_headers"],
        "overall_score": general["score"],
    }

    jd = (job_description or "").strip()
    if jd:
        keyword = _keyword_analysis(resume_text, jd)
        result.update({
            "mode": "targeted",
            "keyword_score": keyword["score"],
            "matched_keywords": keyword["matched"],
            "missing_keywords": keyword["missing"],
            "overall_score": round(0.65 * keyword["score"] + 0.35 * general["score"]),
        })

    return result
