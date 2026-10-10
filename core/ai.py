"""
core/ai.py
AI backend for resume rewriting, cover letters, ATS keyword-gap analysis, and
interview prep. Two providers, switched with one .env variable:

  AI_PROVIDER=ollama     (default) -- fully local, zero API cost, nothing
                          leaves your machine. Requires Ollama running with a
                          model pulled. Quality depends on the model you pick
                          (see README for hardware-tiered recommendations).
  AI_PROVIDER=anthropic  -- Claude API. Costs a small amount per call, needs
                          no local hardware, generally higher-quality output.
"""

import json
import os
import re

try:  # make sure .env is loaded even if this module is imported before app.py calls load_dotenv()
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# Settings are read at call time (not import time) so .env changes are always honoured.
def _provider() -> str:
    return os.getenv("AI_PROVIDER", "ollama").strip().lower()


def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


def _ollama_host() -> str:
    return os.getenv("OLLAMA_HOST", "http://localhost:11434")


def _anthropic_model() -> str:
    # Override with ANTHROPIC_MODEL in .env (e.g. a cheaper/faster or higher-quality Claude model).
    return os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")


def _ask(system: str, user: str, max_tokens: int = 2000) -> str:
    provider = _provider()
    if provider == "anthropic":
        return _ask_anthropic(system, user, max_tokens)
    if provider == "ollama":
        return _ask_ollama(system, user, max_tokens)
    raise RuntimeError(f"Unknown AI_PROVIDER '{provider}'. Use 'ollama' or 'anthropic'.")


def _extract_json(raw: str):
    """Parse JSON from a model reply, tolerating code fences and surrounding prose."""
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Try the outermost structure first: whichever of "[" / "{" appears earliest.
    pairs = sorted((("[", "]"), ("{", "}")),
                   key=lambda p: raw.find(p[0]) if p[0] in raw else len(raw) + 1)
    for open_c, close_c in pairs:
        i, j = raw.find(open_c), raw.rfind(close_c)
        if i != -1 and j > i:
            try:
                return json.loads(raw[i:j + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("no valid JSON found in model output")


def _ask_ollama(system: str, user: str, max_tokens: int) -> str:
    import ollama  # imported lazily so this dependency is optional if you only use Anthropic

    host, model = _ollama_host(), _ollama_model()
    client = ollama.Client(host=host)
    try:
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            # Ollama's default context window is small and silently truncates long
            # resume + job-description prompts, so request a bigger one.
            options={"num_predict": max_tokens,
                     "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "8192"))},
        )
    except Exception as e:
        raise RuntimeError(
            f"Couldn't reach Ollama at {host} with model '{model}'. "
            f"Checklist: (1) is Ollama running? try `ollama serve`. "
            f"(2) is the model pulled? try `ollama pull {model}`. "
            f"Original error: {e}"
        ) from e
    return response["message"]["content"]


def _ask_anthropic(system: str, user: str, max_tokens: int) -> str:
    from anthropic import Anthropic  # imported lazily -- optional if you only use Ollama

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "AI_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set in .env "
            "(get one at https://console.anthropic.com)."
        )
    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=_anthropic_model(),
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


_STRUCTURE_RULES = (
    "CRITICAL: preserve the candidate's original structure. Keep the same "
    "sections, in the same order, with roughly the same amount of content per "
    "section -- do not invent new sections, drop sections, or reorder them. "
    "Your job is to improve the writing and keyword strength, not redesign "
    "the document. Quantify impact ONLY with figures already present in the "
    "original resume; never invent numbers. Use strong action "
    "verbs, remove filler and cliches, avoid first-person pronouns (I, my, "
    "me). Never fabricate skills, employers, dates, or credentials that "
    "aren't in the original resume. Keep section headers on their own line, "
    "and bullets on their own line starting with '- ', so the output can be "
    "reliably converted to a clean document."
)

_ADVANCED_RESUME_RULES = (
    "ADVANCED RESUME OPTIMIZATION RULES:\n"
    "1. IMPACT QUANTIFICATION: Make vague statements more concrete and result-oriented. "
    "   Use numbers, percentages, dollar amounts and timeframes ONLY if they appear in the "
    "   original resume. Where impact is implied but no figure is given, insert a bracketed "
    "   placeholder such as [X%] or [N users] for the candidate to fill in. NEVER invent figures.\n"
    "2. POWER VERBS: Use tier-1 action verbs: Spearheaded, Architected, Orchestrated, "
    "   Pioneered, Accelerated, Drove, Transformed, Scaled, Optimized, Engineered, "
    "   Championed, Delivered, Exceeded, Streamlined.\n"
    "3. KEYWORD DENSITY: Weave in industry-standard terminology naturally throughout "
    "   bullet points — not just in a Skills section. ATS systems score in-context keywords higher.\n"
    "4. SCANNABILITY: Ensure each bullet follows PAR format (Problem/Action/Result) or "
    "   CAR format (Challenge/Action/Result). Each bullet should be 1-2 lines max.\n"
    "5. SUMMARY PUNCH: The professional summary should open with a compelling 2-sentence "
    "   positioning statement that highlights the candidate's unique value proposition "
    "   for this specific role.\n"
    "6. SKILLS OPTIMIZATION: List skills in order of relevance to the target role. "
    "   Group related skills together (e.g., 'Cloud: AWS, GCP, Azure').\n"
    "7. TRUTHFULNESS: NEVER fabricate, exaggerate beyond what the original implies, or "
    "   add credentials not already present. Improve framing only."
)


def improve_resume(resume_text: str, job_description: str = "", target_keywords: str = "") -> str:
    """Rewrites the resume, preserving its original section structure/order.
    Three modes, chosen by what's provided (job_description takes priority
    over target_keywords if both are given):
      - job_description set   -> tailored to that specific role
      - target_keywords set   -> generically optimized toward that role/field
      - neither set            -> general best-practices improvement
    """
    job_description = (job_description or "").strip()
    target_keywords = (target_keywords or "").strip()

    base_system = (
        "You are a world-class resume writer with 15+ years of experience at "
        "top recruiting firms (McKinsey, Google, Meta). You have helped thousands "
        "of candidates land roles at FAANG companies and Fortune 500 firms. "
        + _STRUCTURE_RULES + "\n\n" + _ADVANCED_RESUME_RULES
    )

    if job_description:
        system = base_system + (
            "\n\nTAILORING STRATEGY: Mirror the job description's exact terminology "
            "and keyword phrases in the resume's bullet points and summary — but ONLY "
            "where the candidate's real experience genuinely supports them. Prioritize "
            "the top 10 most distinctive skills/tools mentioned in the JD."
        )
        user = (
            f"JOB DESCRIPTION:\n{job_description}\n\n"
            f"CURRENT RESUME:\n{resume_text}\n\n"
            "Rewrite this resume tailored to the job description above. "
            "Apply all 7 advanced optimization rules. "
            "Return ONLY the rewritten resume text — no commentary before or after."
        )
    elif target_keywords:
        system = base_system + (
            f"\n\nTARGET OPTIMIZATION: The candidate is targeting roles related to: "
            f"{target_keywords}. Frame their existing experience using the standard "
            f"vocabulary of that field. Emphasize transferable skills most valued in that domain."
        )
        user = (
            f"TARGET ROLE / KEYWORDS: {target_keywords}\n\n"
            f"CURRENT RESUME:\n{resume_text}\n\n"
            "Rewrite this resume, optimizing it for the target above using "
            "only the candidate's real, existing experience. Apply all 7 advanced "
            "optimization rules. Return ONLY the rewritten resume text — no commentary."
        )
    else:
        system = base_system + (
            "\n\nGENERAL IMPROVEMENT: Focus on universal resume excellence — "
            "clarity, strong action verbs, quantified results, removing filler, "
            "fixing weak phrasing, and ensuring ATS compatibility."
        )
        user = (
            f"CURRENT RESUME:\n{resume_text}\n\n"
            "Improve this resume using general best practices and all 7 advanced "
            "optimization rules. Return ONLY the rewritten resume text — no commentary."
        )

    return _ask(system, user, max_tokens=4000)


def improve_latex_segments(segments: list, job_description: str = "", target_keywords: str = "") -> dict:
    """Safer than improve_latex(): the AI only ever sees/returns small text
    fragments (bullets, summary), never touches a single LaTeX command.
    segments: list of {"id": ..., "text": ...}. Returns {id: improved_text}.
    """
    job_description = (job_description or "").strip()
    target_keywords = (target_keywords or "").strip()
    target_line = (
        f"Tailor to this job description:\n{job_description}\n" if job_description else
        f"Optimize generically for: {target_keywords}\n" if target_keywords else
        "No specific job/role given -- apply general resume best practices.\n"
    )
    system = (
        "You are a world-class resume writer. You improve resume text fragments. "
        "You'll receive a JSON array of "
        '{"id": ..., "text": ...} objects -- each is one bullet point or '
        "summary paragraph from a resume. Rewrite each 'text' value using these rules:\n"
        "1. Use powerful action verbs (Spearheaded, Architected, Drove, Delivered)\n"
        "2. Use numbers only if present in the original text; otherwise use a placeholder like [X%]. Never invent figures\n"
        "3. Use PAR/CAR format (Problem/Action/Result or Challenge/Action/Result)\n"
        "4. Keep each bullet concise (1-2 lines max)\n"
        "5. Mirror target job keywords naturally\n"
        "6. NEVER fabricate — only improve framing of what's already there\n\n"
        "Return ONLY a JSON array, same order, same ids, same shape: "
        '[{"id": ..., "text": ...}, ...]. No markdown fences, no commentary, '
        "valid JSON only. Do not include LaTeX commands in your output; "
        "plain text is fine, it will be inserted into the document for you."
    )
    user = f"{target_line}\nFRAGMENTS:\n{json.dumps(segments, indent=2)}"
    raw = _ask(system, user, max_tokens=4000).strip()
    try:
        parsed = _extract_json(raw)
    except ValueError as e:
        raise RuntimeError(f"AI didn't return valid JSON: {e}\nRaw output:\n{raw[:500]}")
    if isinstance(parsed, dict):  # some models wrap the list, e.g. {"fragments": [...]}
        parsed = next((v for v in parsed.values() if isinstance(v, list)), [])
    return {str(item["id"]): item["text"] for item in parsed
            if isinstance(item, dict) and "id" in item and isinstance(item.get("text"), str)}


def improve_latex(tex_source: str, job_description: str = "", target_keywords: str = "") -> str:
    """Fallback for templates extract_segments() can't parse (whole-file
    rewrite -- riskier than improve_latex_segments, use that first)."""
    job_description = (job_description or "").strip()
    target_keywords = (target_keywords or "").strip()

    target_line = (
        f"Tailor the wording to this job description:\n{job_description}\n"
        if job_description else
        f"Optimize the wording generically for: {target_keywords}\n"
        if target_keywords else
        "No specific job/role given -- apply general resume best practices.\n"
    )

    system = (
        "You are an expert resume writer editing a LaTeX (.tex) source file. "
        "CRITICAL RULES:\n"
        "1. Preserve the LaTeX document EXACTLY: every \\command, package, "
        "environment, color, spacing, and structural element must remain "
        "unchanged. Do not add/remove \\item, \\section, or any commands.\n"
        "2. Only edit the human-readable text: bullet content, summary "
        "paragraph, skill list text.\n"
        "3. Any special LaTeX characters YOU introduce in new text must be "
        "escaped exactly like the surrounding document does it (% as \\%, "
        "$ as \\$, & as \\&, # as \\#, _ as \\_) -- an unescaped % silently "
        "truncates the rest of the line when compiled, so this is critical.\n"
        "4. Never fabricate skills, employers, dates, or credentials not "
        "already in the original.\n"
        "5. Apply power verbs, quantified impact, and PAR format to bullets.\n"
        "6. Return the COMPLETE modified .tex file only -- no explanation, "
        "no code fence, nothing before \\documentclass or after \\end{document}."
    )
    user = f"{target_line}\nLATEX RESUME SOURCE:\n{tex_source}"
    return _ask(system, user, max_tokens=6000)


def generate_cover_letter(resume_text: str, job_description: str, company: str = "", role: str = "") -> str:
    """Generate a tailored, compelling cover letter."""
    system = (
        "You are an expert career coach who writes concise, specific, non-generic cover "
        "letters. RULES:\n"
        "1. Open with a compelling hook that connects a specific achievement from the "
        "candidate's background to a specific need in the job description.\n"
        "2. NEVER use clichés: 'excited to apply', 'passionate about', 'team player', "
        "'hard worker', 'results-driven'. These are red flags to recruiters.\n"
        "3. Structure: Hook paragraph → 2 evidence paragraphs (specific accomplishments "
        "matching JD requirements) → Closing with clear call to action.\n"
        "4. Keep it to 3-4 short paragraphs, max 300 words.\n"
        "5. Use the hiring manager's perspective: What problem does hiring this person solve?\n"
        "6. Never fabricate experience the candidate doesn't have.\n"
        "7. Make it sound human and conversational, not robotic or formulaic."
    )
    user = (
        f"COMPANY: {company or 'the company'}\nROLE: {role or 'the role'}\n\n"
        f"JOB DESCRIPTION:\n{job_description}\n\n"
        f"CANDIDATE RESUME:\n{resume_text}\n\n"
        "Write the cover letter now. Return only the letter text, starting with "
        "'Dear Hiring Manager,' (or a specific name if mentioned in the JD)."
    )
    return _ask(system, user, max_tokens=1500)


def keyword_gap_analysis(resume_text: str, job_description: str) -> str:
    system = (
        "You are a senior ATS (Applicant Tracking System) specialist and recruiter. "
        "You analyze resumes against job descriptions with expert precision. "
        "Be specific, actionable, and concise."
    )
    user = (
        f"JOB DESCRIPTION:\n{job_description}\n\nRESUME:\n{resume_text}\n\n"
        "Provide a comprehensive keyword gap analysis with:\n"
        "1. **ATS Keyword Score**: Estimated match percentage and rating (Poor/Fair/Good/Excellent)\n"
        "2. **Top 12 JD Keywords/Skills** (ranked by importance, mark which appear in resume ✅/❌)\n"
        "3. **Critical Missing Keywords** (3-5 must-add items that will significantly boost ATS score)\n"
        "4. **Keyword Context Tips**: For each missing keyword, suggest ONE specific bullet point "
        "rewrite that naturally incorporates it (only if the candidate's experience supports it)\n"
        "5. **Quick Wins**: 2-3 highest-impact changes to make right now\n"
        "Format with clear headers and bullet points for easy reading."
    )
    return _ask(system, user, max_tokens=1500)


def general_resume_review(resume_text: str) -> str:
    """Deeper AI critique for when there's no job description to compare
    against -- general ATS/best-practices review instead of a keyword gap."""
    system = (
        "You are a senior recruiter at a top-tier firm and ATS optimization expert. "
        "You've reviewed 10,000+ resumes and know exactly what separates a resume "
        "that gets interviews from one that gets rejected in 7 seconds."
    )
    user = (
        f"RESUME:\n{resume_text}\n\n"
        "Provide a comprehensive resume audit with:\n"
        "1. **Overall Grade**: Letter grade (A-F) with 2-sentence executive summary\n"
        "2. **ATS Compatibility Score**: /100 with specific technical issues\n"
        "3. **Top 3 Strengths**: What's genuinely working well (be specific)\n"
        "4. **Top 5 Critical Issues**: Ranked by impact, with specific line-by-line examples\n"
        "5. **Before/After Examples**: Rewrite 2 of the weakest bullets to show the difference\n"
        "6. **Formatting Red Flags**: Any ATS parsing issues, layout problems\n"
        "7. **One-Week Action Plan**: Prioritized list of improvements\n"
        "Format with clear headers and use markdown for emphasis."
    )
    return _ask(system, user, max_tokens=2000)


def generate_interview_questions(resume_text: str, job_description: str) -> str:
    system = (
        "You are a senior hiring manager and behavioral interview specialist who has "
        "conducted 500+ interviews for technical and non-technical roles."
    )
    user = (
        f"JOB DESCRIPTION:\n{job_description}\n\nCANDIDATE RESUME:\n{resume_text}\n\n"
        "Generate a comprehensive interview prep guide with:\n"
        "1. **3 Behavioral Questions** (STAR format): Pick scenarios that probe "
        "the exact competencies this role requires\n"
        "2. **3 Technical/Role-Specific Questions**: Based on the JD's core requirements\n"
        "3. **2 Probing Questions**: About gaps, transitions, or inconsistencies in the resume\n"
        "4. **2 'Curveball' Questions**: Unexpected questions this interviewer might ask\n"
        "For each question:\n"
        "  - The question itself\n"
        "  - Why they're asking it (what they're really evaluating)\n"
        "  - What a strong answer must include\n"
        "  - One example talking point from this candidate's background\n\n"
        "Also include: **3 Strong Questions to Ask the Interviewer** that show strategic thinking."
    )
    return _ask(system, user, max_tokens=2500)


def mock_interview_feedback(question: str, answer: str, resume_text: str) -> str:
    system = (
        "You are an elite interview coach who has helped candidates land jobs at Google, "
        "McKinsey, Goldman Sachs, and top startups. You give direct, actionable feedback "
        "using the STAR framework (Situation, Task, Action, Result)."
    )
    user = (
        f"INTERVIEW QUESTION:\n{question}\n\nCANDIDATE'S ANSWER:\n{answer}\n\n"
        f"CANDIDATE RESUME (for context):\n{resume_text}\n\n"
        "Provide coaching feedback with:\n"
        "1. **Overall Score**: /10 with one-line verdict\n"
        "2. **STAR Framework Analysis**: What's present ✅ and missing ❌ in each component\n"
        "3. **Strengths**: What worked well in this answer\n"
        "4. **Critical Gaps**: What's missing that interviewers will notice\n"
        "5. **Rewritten Opening**: A stronger first 2-3 sentences for this answer\n"
        "6. **Pro Tip**: One specific technique to make this answer memorable\n"
        "Be direct and specific — vague feedback doesn't help candidates improve."
    )
    return _ask(system, user, max_tokens=1200)


def generate_linkedin_message(resume_text: str, job_description: str, company: str = "", role: str = "") -> str:
    """Generate a personalized LinkedIn outreach message for recruiters/hiring managers."""
    system = (
        "You are a networking expert who writes personalized, non-spammy LinkedIn "
        "outreach messages. You know that short, specific, value-focused messages "
        "get 5x the response rate of generic ones."
    )
    user = (
        f"COMPANY: {company or 'the company'}\nROLE: {role or 'the role'}\n\n"
        f"JOB DESCRIPTION:\n{job_description}\n\n"
        f"MY BACKGROUND:\n{resume_text}\n\n"
        "Write a LinkedIn connection message (max 300 chars) AND a follow-up InMail (max 400 words). "
        "The connection message should be curiosity-inducing and personal. "
        "The InMail should open with a specific connection point (mutual interest, "
        "shared background, or specific company achievement), then pivot to value. "
        "NO generic phrases like 'I came across your profile' or 'I'm a fan of your work'. "
        "Return both messages labeled clearly."
    )
    return _ask(system, user, max_tokens=800)


def score_job_fit(resume_text: str, job_description: str) -> dict:
    """AI-powered job fit scoring with detailed breakdown."""
    system = (
        "You are a recruitment AI that scores candidate-job fit with precision. "
        "Return ONLY valid JSON, no markdown fences, no commentary."
    )
    user = (
        f"JOB DESCRIPTION:\n{job_description}\n\nRESUME:\n{resume_text}\n\n"
        "Score the fit and return JSON exactly like this:\n"
        '{"overall_score": 85, "skills_match": 80, "experience_match": 90, '
        '"education_match": 85, "culture_fit": 80, '
        '"strengths": ["point1", "point2", "point3"], '
        '"gaps": ["gap1", "gap2"], '
        '"recommendation": "Strong Apply|Apply|Apply with Cover Letter|Skip", '
        '"reasoning": "2-3 sentence explanation"}'
    )
    raw = _ask(system, user, max_tokens=600).strip()
    try:
        data = _extract_json(raw)
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object")

        def _num(key):
            try:
                return max(0, min(100, int(float(data.get(key, 0)))))
            except (TypeError, ValueError):
                return 0

        return {
            "overall_score": _num("overall_score"),
            "skills_match": _num("skills_match"),
            "experience_match": _num("experience_match"),
            "education_match": _num("education_match"),
            "culture_fit": _num("culture_fit"),
            "strengths": [str(x) for x in data.get("strengths", [])] if isinstance(data.get("strengths"), list) else [],
            "gaps": [str(x) for x in data.get("gaps", [])] if isinstance(data.get("gaps"), list) else [],
            "recommendation": str(data.get("recommendation", "")),
            "reasoning": str(data.get("reasoning", "")),
        }
    except ValueError:
        return {
            "overall_score": 0,
            "skills_match": 0,
            "experience_match": 0,
            "education_match": 0,
            "culture_fit": 0,
            "strengths": [],
            "gaps": [],
            "recommendation": "Error",
            "reasoning": f"Could not parse AI response: {raw[:200]}"
        }
