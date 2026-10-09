"""
core/latex_template.py
Renders a structured Resume (core.resume_model.Resume) into a from-scratch
LaTeX document. Used for PDF/DOCX/TXT uploads, which have no original .tex
to preserve, so we build a clean, professional one instead of the plain
docx/pdf template. Deliberately uses ONLY packages/fonts guaranteed present
in any LaTeX install (no libertinus, no lmodern) -- default Computer Modern
fonts plus fontawesome5 for icons, both confirmed to install cleanly.
"""

import re


def _tex_escape(s: str) -> str:
    return re.sub(r"([%$&#_{}])", r"\\\1", s or "")


def render_latex(resume) -> str:
    c = resume.contact
    out = [r"""\documentclass[10pt,a4paper]{article}
\usepackage[a4paper,left=0.6in,right=0.6in,top=0.5in,bottom=0.5in]{geometry}
\usepackage[T1]{fontenc}
\usepackage{xcolor}
\usepackage[hidelinks]{hyperref}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{fontawesome5}
\usepackage{tabularx}
\pagestyle{empty}
\setlength{\parindent}{0pt}
\definecolor{accent}{HTML}{0F4C81}
\titleformat{\section}{\large\bfseries\color{accent}}{}{0em}{}[\titlerule]
\titlespacing*{\section}{0pt}{6pt}{2pt}
\setlist[itemize]{leftmargin=1.1em,itemsep=1pt,topsep=2pt,parsep=0pt}
\begin{document}
"""]

    out.append(r"\begin{center}" + "\n")
    out.append(r"{\LARGE\bfseries " + _tex_escape(c.name) + r"}\\[4pt]" + "\n")
    bits = []
    if c.email:
        bits.append(r"\faEnvelope\ \href{mailto:%s}{%s}" % (c.email, _tex_escape(c.email)))
    if c.phone:
        bits.append(r"\faPhone\ " + _tex_escape(c.phone))
    if c.website:
        bits.append(r"\faGlobe\ \href{https://%s}{%s}" % (c.website, _tex_escape(c.website)))
    if c.linkedin:
        handle = c.linkedin.rstrip("/").split("/")[-1]
        bits.append(r"\faLinkedin\ \href{https://linkedin.com/in/%s}{%s}" % (handle, _tex_escape(c.linkedin)))
    if c.github:
        bits.append(r"\faGithub\ \href{https://%s}{%s}" % (c.github, _tex_escape(c.github)))
    if c.location:
        bits.append(r"\faMapMarker*\ " + _tex_escape(c.location))
    out.append(" \\quad ".join(bits) + "\n")
    out.append(r"\end{center}" + "\n\n")

    for sec in resume.sections:
        out.append(r"\section*{%s}" % _tex_escape(sec.heading) + "\n")
        for e in sec.entries:
            out.append(r"\noindent\begin{tabularx}{\textwidth}{Xr}" + "\n")
            out.append(r"\textbf{%s} & %s \\" % (_tex_escape(e.title), _tex_escape(e.dates)) + "\n")
            if e.subtitle or e.tags:
                out.append(r"\textit{%s} & \\" % _tex_escape(e.subtitle or e.tags) + "\n")
            out.append(r"\end{tabularx}" + "\n")
            if e.bullets:
                out.append(r"\begin{itemize}" + "\n")
                for b in e.bullets:
                    out.append(r"\item " + _tex_escape(b) + "\n")
                out.append(r"\end{itemize}" + "\n")
            out.append(r"\vspace{2pt}" + "\n")
        for l in sec.lines:
            out.append(_tex_escape(l) + r"\\" + "\n")
        out.append("\n")

    out.append(r"\end{document}" + "\n")
    return "".join(out)
