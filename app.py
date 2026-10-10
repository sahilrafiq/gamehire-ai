"""
app.py
Streamlit UI — cinematic anime-themed design with glassmorphism, gradient
animations, and a professional modern aesthetic.

Run with:
    streamlit run app.py
"""

import html as _html
import os
import tempfile
import threading
import queue
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # must run BEFORE importing core.* so .env settings are visible to them

from core import ai, ats, jobs, latex_editor, latex_generator, parser, tracker
from core.applier import ApplyConfig, ApplyResult, batch_apply, apply_to_job, _is_playwright_available


def _esc(value) -> str:
    """HTML-escape any text (job titles, keywords, ...) before putting it in unsafe_allow_html markup."""
    return _html.escape(str(value if value is not None else ""), quote=True)


def _safe_url(url) -> str:
    """Escaped URL, or '#' unless it is a plain http(s) link (blocks javascript: URLs)."""
    url = str(url or "").strip()
    return _esc(url) if url.lower().startswith(("http://", "https://")) else "#"


# ─────────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GameHire — AI Job Search Copilot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────
#  CINEMATIC ANIME-THEMED CSS
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── CSS Variables ── */
:root {
    --bg-deep:       #04060f;
    --bg-base:       #070c1a;
    --bg-card:       rgba(10, 17, 40, 0.85);
    --bg-hover:      rgba(20, 30, 70, 0.90);
    --glass:         rgba(255, 255, 255, 0.04);
    --glass-border:  rgba(255, 255, 255, 0.08);
    --glass-hover:   rgba(255, 255, 255, 0.09);

    --neon-blue:     #00cfff;
    --neon-purple:   #9b5de5;
    --neon-pink:     #f72585;
    --neon-cyan:     #4cc9f0;
    --neon-gold:     #ffd60a;
    --neon-green:    #43e97b;

    --grad-primary:  linear-gradient(135deg, #9b5de5 0%, #00cfff 50%, #f72585 100%);
    --grad-card:     linear-gradient(145deg, rgba(155,93,229,0.15) 0%, rgba(0,207,255,0.08) 100%);
    --grad-accent:   linear-gradient(90deg, #9b5de5, #00cfff);
    --grad-gold:     linear-gradient(90deg, #ffd60a, #ff9500);

    --text-primary:  #e8eaf6;
    --text-secondary: #8fa3c8;
    --text-muted:    #4a6080;

    --radius-sm:     8px;
    --radius-md:     14px;
    --radius-lg:     20px;
    --radius-xl:     28px;

    --shadow-neon:   0 0 20px rgba(0, 207, 255, 0.25), 0 0 60px rgba(155, 93, 229, 0.15);
    --shadow-card:   0 8px 32px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.05);
    --transition:    all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ── Global Reset & Body ── */
*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stApp"], .stApp {
    background: var(--bg-deep) !important;
    font-family: 'Outfit', sans-serif !important;
    color: var(--text-primary) !important;
}

/* Animated gradient background */
[data-testid="stApp"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 80% 60% at 20% 10%, rgba(155,93,229,0.12) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 80% 90%, rgba(0,207,255,0.10) 0%, transparent 60%),
        radial-gradient(ellipse 50% 40% at 50% 50%, rgba(247,37,133,0.06) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
    animation: bgPulse 8s ease-in-out infinite alternate;
}

@keyframes bgPulse {
    0%   { opacity: 0.7; }
    100% { opacity: 1.0; }
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-deep); }
::-webkit-scrollbar-thumb { background: rgba(155,93,229,0.5); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--neon-purple); }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
.stDeployButton { display: none !important; }

/* ── Main container ── */
.block-container {
    padding: 0 2rem 3rem !important;
    max-width: 1400px !important;
    margin: 0 auto !important;
    position: relative;
    z-index: 1;
}

/* ── HERO HEADER ── */
.game-hero {
    text-align: center;
    padding: 3rem 1rem 2rem;
    position: relative;
    overflow: hidden;
}

.game-hero::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 600px;
    height: 200px;
    background: radial-gradient(ellipse, rgba(155,93,229,0.2) 0%, transparent 70%);
    pointer-events: none;
    animation: heroGlow 4s ease-in-out infinite alternate;
}

@keyframes heroGlow {
    0%   { transform: translate(-50%, -50%) scale(1); opacity: 0.6; }
    100% { transform: translate(-50%, -50%) scale(1.2); opacity: 1; }
}

.game-logo {
    font-size: 3.2rem;
    font-weight: 900;
    letter-spacing: -1px;
    background: var(--grad-primary);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    display: inline-block;
    line-height: 1;
    margin-bottom: 0.4rem;
    animation: logoShimmer 3s ease infinite;
    background-size: 200% auto;
}

@keyframes logoShimmer {
    0%   { background-position: 0% center; }
    50%  { background-position: 100% center; }
    100% { background-position: 0% center; }
}

.game-tagline {
    color: var(--text-secondary);
    font-size: 1rem;
    font-weight: 400;
    letter-spacing: 0.05em;
    margin-top: 0.3rem;
}

.game-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 14px;
    border-radius: 100px;
    border: 1px solid rgba(0, 207, 255, 0.3);
    background: rgba(0, 207, 255, 0.08);
    color: var(--neon-cyan);
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}

.game-badge::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--neon-cyan);
    animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.5; transform: scale(1.5); }
}

/* ── STAT CARDS (dashboard row) ── */
.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 12px;
    margin: 1.5rem 0;
}

.stat-card {
    background: var(--glass);
    border: 1px solid var(--glass-border);
    border-radius: var(--radius-md);
    padding: 1rem 0.8rem;
    text-align: center;
    backdrop-filter: blur(12px);
    transition: var(--transition);
    position: relative;
    overflow: hidden;
}

.stat-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--grad-accent);
    border-radius: 2px 2px 0 0;
    opacity: 0;
    transition: opacity 0.3s;
}

.stat-card:hover { 
    border-color: rgba(155,93,229,0.35);
    transform: translateY(-2px);
    box-shadow: var(--shadow-neon);
}

.stat-card:hover::before { opacity: 1; }

.stat-number {
    font-size: 1.8rem;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 4px;
}

.stat-label {
    font-size: 0.72rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--glass) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius-lg) !important;
    padding: 6px !important;
    gap: 4px !important;
    backdrop-filter: blur(12px);
    margin-bottom: 1.5rem !important;
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-secondary) !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 8px 18px !important;
    border: none !important;
    transition: var(--transition) !important;
    white-space: nowrap;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-primary) !important;
    background: var(--glass-hover) !important;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(155,93,229,0.3), rgba(0,207,255,0.2)) !important;
    color: var(--neon-cyan) !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 12px rgba(0, 207, 255, 0.2) !important;
}

.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-border"]    { display: none !important; }

/* ── SECTION HEADERS ── */
.section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 1.2rem;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid var(--glass-border);
}

.section-icon {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    flex-shrink: 0;
}

.section-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
}

.section-subtitle {
    font-size: 0.82rem;
    color: var(--text-muted);
    margin: 2px 0 0;
}

/* ── GLASS CARDS ── */
.glass-card {
    background: var(--bg-card);
    border: 1px solid var(--glass-border);
    border-radius: var(--radius-lg);
    padding: 1.4rem 1.6rem;
    backdrop-filter: blur(16px);
    box-shadow: var(--shadow-card);
    margin-bottom: 1rem;
    transition: var(--transition);
    position: relative;
    overflow: hidden;
}

.glass-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.12), transparent);
}

.glass-card:hover {
    border-color: rgba(155,93,229,0.25);
    box-shadow: var(--shadow-neon);
}

/* ── JOB RESULT CARDS ── */
.job-card {
    background: var(--glass);
    border: 1px solid var(--glass-border);
    border-radius: var(--radius-md);
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
    transition: var(--transition);
    position: relative;
    overflow: hidden;
}

.job-card::after {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: var(--grad-accent);
    border-radius: 0 2px 2px 0;
    opacity: 0;
    transition: opacity 0.3s;
}

.job-card:hover {
    border-color: rgba(0,207,255,0.3);
    background: var(--glass-hover);
    transform: translateX(4px);
}

.job-card:hover::after { opacity: 1; }

.job-title { font-size: 0.95rem; font-weight: 700; color: var(--text-primary); }
.job-company { font-size: 0.83rem; color: var(--neon-cyan); font-weight: 600; }
.job-meta { font-size: 0.75rem; color: var(--text-muted); margin-top: 4px; }

/* Platform badges */
.platform-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 100px;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.badge-remotive { background: rgba(67,233,123,0.12); color: #43e97b; border: 1px solid rgba(67,233,123,0.2); }
.badge-adzuna { background: rgba(0,207,255,0.12); color: #00cfff; border: 1px solid rgba(0,207,255,0.2); }
.badge-jooble { background: rgba(155,93,229,0.12); color: #9b5de5; border: 1px solid rgba(155,93,229,0.2); }
.badge-arbeitnow { background: rgba(255,214,10,0.12); color: #ffd60a; border: 1px solid rgba(255,214,10,0.2); }

/* ── FIT SCORE RING ── */
.fit-ring {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 72px;
    height: 72px;
    border-radius: 50%;
    font-weight: 800;
    font-size: 1.2rem;
    position: relative;
}

.fit-ring.excellent { 
    background: conic-gradient(#43e97b var(--pct), rgba(67,233,123,0.1) 0);
    color: #43e97b;
    box-shadow: 0 0 16px rgba(67,233,123,0.3);
}
.fit-ring.good { 
    background: conic-gradient(#00cfff var(--pct), rgba(0,207,255,0.1) 0);
    color: #00cfff;
    box-shadow: 0 0 16px rgba(0,207,255,0.3);
}
.fit-ring.fair { 
    background: conic-gradient(#ffd60a var(--pct), rgba(255,214,10,0.1) 0);
    color: #ffd60a;
    box-shadow: 0 0 16px rgba(255,214,10,0.3);
}
.fit-ring.poor { 
    background: conic-gradient(#f72585 var(--pct), rgba(247,37,133,0.1) 0);
    color: #f72585;
    box-shadow: 0 0 16px rgba(247,37,133,0.3);
}

/* ── BUTTONS ── */
.stButton > button {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--glass-border) !important;
    transition: var(--transition) !important;
    background: var(--glass) !important;
    color: var(--text-primary) !important;
    padding: 0.5rem 1.2rem !important;
}

.stButton > button:hover {
    border-color: rgba(155,93,229,0.4) !important;
    background: rgba(155,93,229,0.12) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(155,93,229,0.2) !important;
}

/* Primary button — gradient */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #9b5de5, #00cfff) !important;
    border: none !important;
    color: #fff !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 20px rgba(155,93,229,0.35) !important;
}

.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #b06ef0, #33d6ff) !important;
    box-shadow: 0 6px 28px rgba(155,93,229,0.5) !important;
    transform: translateY(-2px) !important;
}

/* Auto-apply CTA button */
.stButton > button[data-auto="true"],
button.auto-apply-btn {
    background: linear-gradient(135deg, #f72585, #9b5de5) !important;
    border: none !important;
    color: #fff !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 20px rgba(247,37,133,0.35) !important;
}

/* Download buttons */
.stDownloadButton > button {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    border-radius: var(--radius-md) !important;
    background: rgba(67,233,123,0.1) !important;
    border: 1px solid rgba(67,233,123,0.25) !important;
    color: var(--neon-green) !important;
    transition: var(--transition) !important;
}

.stDownloadButton > button:hover {
    background: rgba(67,233,123,0.2) !important;
    box-shadow: 0 0 16px rgba(67,233,123,0.25) !important;
    transform: translateY(-1px) !important;
}

/* ── FORM INPUTS ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.9rem !important;
    transition: var(--transition) !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: rgba(155,93,229,0.5) !important;
    box-shadow: 0 0 0 2px rgba(155,93,229,0.15) !important;
    outline: none !important;
}

/* Labels */
.stTextInput label, .stTextArea label, .stSelectbox label,
.stFileUploader label, .stCheckbox label {
    color: var(--text-secondary) !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    margin-bottom: 4px !important;
}

/* ── FILE UPLOADER ── */
[data-testid="stFileUploader"] {
    background: rgba(155,93,229,0.04) !important;
    border: 2px dashed rgba(155,93,229,0.25) !important;
    border-radius: var(--radius-md) !important;
    padding: 1rem !important;
    transition: var(--transition) !important;
}

[data-testid="stFileUploader"]:hover {
    border-color: rgba(155,93,229,0.5) !important;
    background: rgba(155,93,229,0.08) !important;
}

/* ── METRICS ── */
[data-testid="stMetric"] {
    background: var(--glass) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius-md) !important;
    padding: 1rem !important;
    backdrop-filter: blur(8px) !important;
}

[data-testid="stMetricValue"] {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 800 !important;
    font-size: 2rem !important;
    background: var(--grad-accent);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

[data-testid="stMetricLabel"] {
    color: var(--text-muted) !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

/* ── ALERTS / INFO / SUCCESS / WARNING ── */
.stAlert, [data-testid="stNotification"] {
    border-radius: var(--radius-md) !important;
    border-left-width: 3px !important;
    font-family: 'Outfit', sans-serif !important;
}

/* Success */
[data-baseweb="notification"][kind="positive"] {
    background: rgba(67,233,123,0.08) !important;
    border-color: var(--neon-green) !important;
}

/* Info */
[data-baseweb="notification"][kind="info"],
.stInfo {
    background: rgba(0,207,255,0.08) !important;
    border-color: var(--neon-cyan) !important;
}

/* Warning */
[data-baseweb="notification"][kind="warning"] {
    background: rgba(255,214,10,0.08) !important;
    border-color: var(--neon-gold) !important;
}

/* Error */
[data-baseweb="notification"][kind="negative"] {
    background: rgba(247,37,133,0.08) !important;
    border-color: var(--neon-pink) !important;
}

/* ── EXPANDER ── */
details {
    background: var(--glass) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius-md) !important;
    overflow: hidden !important;
}

details summary {
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
    padding: 0.7rem 1rem !important;
    cursor: pointer !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.88rem !important;
    transition: var(--transition) !important;
}

details summary:hover { color: var(--text-primary) !important; }
details[open] summary { color: var(--neon-cyan) !important; }

/* ── SPINNER ── */
.stSpinner > div {
    border-top-color: var(--neon-purple) !important;
}

/* ── PROGRESS / STATUS INDICATORS ── */
.apply-status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 12px;
    border-radius: 100px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.status-saved     { background: rgba(143,163,200,0.12); color: #8fa3c8; border: 1px solid rgba(143,163,200,0.2); }
.status-applied   { background: rgba(0,207,255,0.12);   color: #00cfff; border: 1px solid rgba(0,207,255,0.2); }
.status-interview { background: rgba(155,93,229,0.12);  color: #9b5de5; border: 1px solid rgba(155,93,229,0.2); }
.status-offer     { background: rgba(67,233,123,0.12);  color: #43e97b; border: 1px solid rgba(67,233,123,0.2); }
.status-rejected  { background: rgba(247,37,133,0.12);  color: #f72585; border: 1px solid rgba(247,37,133,0.2); }

/* ── DIVIDER ── */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent) !important;
    margin: 1.5rem 0 !important;
}

/* ── CODE / MONO TEXT ── */
code, pre, .stCodeBlock {
    font-family: 'JetBrains Mono', monospace !important;
    background: rgba(0,0,0,0.4) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius-sm) !important;
}

/* ── ATS SCORE BAR ── */
.ats-bar-wrap {
    background: rgba(255,255,255,0.05);
    border-radius: 100px;
    height: 8px;
    margin: 6px 0 12px;
    overflow: hidden;
}

.ats-bar-fill {
    height: 100%;
    border-radius: 100px;
    transition: width 1s ease;
    background: var(--grad-accent);
}

/* ── CHECK LIST ── */
.check-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    font-size: 0.875rem;
    color: var(--text-secondary);
    border-bottom: 1px solid rgba(255,255,255,0.03);
}

.check-item .check-icon { font-size: 1rem; flex-shrink: 0; }
.check-item.pass { color: var(--neon-green); }
.check-item.fail { color: var(--text-muted); }

/* ── TRACKER ROW ── */
.tracker-row {
    background: var(--glass);
    border: 1px solid var(--glass-border);
    border-radius: var(--radius-md);
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.6rem;
    transition: var(--transition);
    display: grid;
    grid-template-columns: 1fr 1fr auto;
    gap: 1rem;
    align-items: center;
}

.tracker-row:hover {
    border-color: rgba(155,93,229,0.25);
    background: var(--bg-hover);
}

/* ── PIPELINE FUNNEL ── */
.pipeline {
    display: flex;
    gap: 6px;
    margin: 1rem 0;
    align-items: stretch;
}

.pipeline-stage {
    flex: 1;
    background: var(--glass);
    border: 1px solid var(--glass-border);
    border-radius: var(--radius-sm);
    padding: 0.7rem 0.5rem;
    text-align: center;
    position: relative;
    transition: var(--transition);
}

.pipeline-stage:not(:last-child)::after {
    content: '›';
    position: absolute;
    right: -10px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-muted);
    font-size: 1.2rem;
    z-index: 1;
}

.pipeline-count {
    font-size: 1.4rem;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 4px;
}

.pipeline-label {
    font-size: 0.65rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
}

/* ── ANIME DECORATIVE ELEMENTS ── */
.deco-line {
    height: 1px;
    background: var(--grad-accent);
    border-radius: 1px;
    margin: 0.5rem 0;
    opacity: 0.4;
}

/* Column gap fix */
[data-testid="column"] { padding: 0 0.4rem !important; }
[data-testid="column"]:first-child { padding-left: 0 !important; }
[data-testid="column"]:last-child  { padding-right: 0 !important; }

/* Selectbox styling */
.stSelectbox [data-baseweb="select"] > div {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius-sm) !important;
}

/* Checkbox */
.stCheckbox > label { color: var(--text-secondary) !important; font-size: 0.88rem !important; }

/* Markdown headings inside tabs */
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    color: var(--text-primary) !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
}

.stMarkdown h2 {
    font-size: 1.1rem !important;
    border-bottom: 1px solid var(--glass-border) !important;
    padding-bottom: 0.4rem !important;
    margin-top: 1.2rem !important;
}

/* Subheader override */
h2[data-testid="stHeading"], .stSubheader {
    color: var(--text-primary) !important;
    font-family: 'Outfit', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
#  SESSION STATE DEFAULTS
# ─────────────────────────────────────────────────────────────────
defaults = {
    "resume_text": "",
    "jd_text": "",
    "original_ext": ".docx",
    "target_keywords": "",
    "job_results": [],
    "selected_jobs": set(),
    "cover_letter": "",
    "fit_scores": {},
    "apply_log": [],
    "auto_apply_config": {},
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────
#  HERO HEADER
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="game-hero">
    <div class="game-badge">⚡ AI-Powered · Local & Private</div>
    <div class="game-logo">⚡ GameHire</div>
    <div class="game-tagline">Cinematic AI Job Search Copilot · Resume · ATS · Auto-Apply · Tracker</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
#  QUICK STATS BAR
# ─────────────────────────────────────────────────────────────────
stats = tracker.get_stats()
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
stat_data = [
    (c1, stats["total"],        "Total",       "var(--text-primary)"),
    (c2, stats["saved"],        "Saved",       "#8fa3c8"),
    (c3, stats["applied"],      "Applied",     "var(--neon-cyan)"),
    (c4, stats["interviewing"], "Interviews",  "var(--neon-purple)"),
    (c5, stats["offer"],        "Offers",      "var(--neon-green)"),
    (c6, stats["rejected"],     "Rejected",    "var(--neon-pink)"),
    (c7, stats["auto_applied"], "Auto-Applied","var(--neon-gold)"),
]
for col, num, label, color in stat_data:
    with col:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number" style="color:{color}">{num}</div>
            <div class="stat-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div class='deco-line'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📄 Resume & ATS",
    "✨ AI Improver",
    "📝 Cover Letter",
    "🔍 Job Search",
    "🤖 Auto-Apply",
    "🎙️ Interview Prep",
    "📊 Tracker",
])

# ═══════════════════════════════════════════════════════════════
#  TAB 1 — Resume & ATS
# ═══════════════════════════════════════════════════════════════
with tab1:
    st.markdown("""
    <div class="section-header">
        <div class="section-icon" style="background:linear-gradient(135deg,rgba(0,207,255,0.2),rgba(155,93,229,0.2))">📄</div>
        <div>
            <div class="section-title">Resume Upload & ATS Analysis</div>
            <div class="section-subtitle">Upload your resume and optionally paste a job description for targeted scoring</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        uploaded = st.file_uploader(
            "Resume (.pdf, .docx, or .txt)",
            type=["pdf", "docx", "txt"],
            key="resume_upload"
        )
        if uploaded is not None:
            suffix = Path(uploaded.name).suffix
            st.session_state.original_ext = suffix if suffix in (".pdf", ".docx") else ".docx"
            # Parse only when a NEW file is uploaded. Re-parsing on every rerun would
            # overwrite whatever the user has edited in the text box below.
            upload_id = (uploaded.name, uploaded.size)
            if st.session_state.get("_parsed_upload") != upload_id:
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded.getvalue())
                        tmp_path = tmp.name
                    st.session_state.resume_text = parser.extract_text(tmp_path)
                    st.session_state["_parsed_upload"] = upload_id
                except Exception as e:
                    st.error(str(e))
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        os.remove(tmp_path)  # don't leave resumes lying around in the temp folder
            if st.session_state.get("_parsed_upload") == upload_id:
                wc = len(st.session_state.resume_text.split())
                st.success(f"✅ Loaded **{uploaded.name}** — {wc} words extracted")

        st.text_area(
            "Resume text (auto-filled, editable)",
            key="resume_text",
            height=280,
            placeholder="Paste your resume text here, or upload a file above...",
        )

    with col2:
        st.session_state.jd_text = st.text_area(
            "Job description (optional — enables role-specific ATS scoring)",
            value=st.session_state.jd_text,
            height=350,
            placeholder="Paste the job description here for targeted keyword matching and ATS scoring...",
        )

    has_resume = bool(st.session_state.resume_text.strip())
    has_jd     = bool(st.session_state.jd_text.strip())

    btn_col1, btn_col2, btn_col3 = st.columns(3)
    run_ats   = btn_col1.button("⚡ Run ATS Score", type="primary", use_container_width=True)
    run_kw    = btn_col2.button("🔑 Keyword Gap Analysis", use_container_width=True, disabled=not has_jd)
    run_rev   = btn_col3.button("🔍 General Resume Review", use_container_width=True)

    if run_ats:
        if not has_resume:
            st.warning("Add a resume first.")
        else:
            with st.spinner("Calculating ATS score..."):
                result = ats.score(st.session_state.resume_text, st.session_state.jd_text)

            label = "Role-Specific ATS Score" if result["mode"] == "targeted" else "General ATS Score"
            score_val = result["overall_score"]

            # Score color
            score_color = (
                "var(--neon-green)"  if score_val >= 80 else
                "var(--neon-cyan)"   if score_val >= 60 else
                "var(--neon-gold)"   if score_val >= 40 else
                "var(--neon-pink)"
            )
            score_label = "Excellent" if score_val >= 80 else "Good" if score_val >= 60 else "Fair" if score_val >= 40 else "Needs Work"

            st.markdown(f"""
            <div class="glass-card" style="margin-top:1rem">
                <div style="display:flex;align-items:center;gap:1.5rem;margin-bottom:1rem">
                    <div style="text-align:center">
                        <div style="font-size:3rem;font-weight:900;color:{score_color};line-height:1">{score_val}</div>
                        <div style="font-size:0.7rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em">/100 · {score_label}</div>
                    </div>
                    <div style="flex:1">
                        <div style="font-size:0.9rem;font-weight:700;color:var(--text-primary);margin-bottom:6px">{label}</div>
                        <div class="ats-bar-wrap"><div class="ats-bar-fill" style="width:{score_val}%;background:{'var(--neon-green)' if score_val>=80 else 'var(--neon-cyan)' if score_val>=60 else 'var(--neon-gold)' if score_val>=40 else 'var(--neon-pink)'}"></div></div>
                        <div style="font-size:0.78rem;color:var(--text-muted)">Word count: {result.get('word_count', '–')}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if result["mode"] == "targeted":
                kc1, kc2 = st.columns(2)
                with kc1:
                    st.markdown(f"**🎯 Keyword Match:** `{result['keyword_score']}/100`")
                    matched = result.get("matched_keywords", [])
                    if matched:
                        kw_html = " ".join(f'<span style="background:rgba(67,233,123,0.15);color:#43e97b;padding:2px 8px;border-radius:100px;font-size:0.72rem;margin:2px;display:inline-block">{_esc(kw)}</span>' for kw in matched[:15])
                        st.markdown(f"**Matched:** {kw_html}", unsafe_allow_html=True)
                with kc2:
                    st.markdown(f"**📋 Best Practices:** `{result['general_score']}/100`")
                    missing = result.get("missing_keywords", [])
                    if missing:
                        kw_html = " ".join(f'<span style="background:rgba(247,37,133,0.15);color:#f72585;padding:2px 8px;border-radius:100px;font-size:0.72rem;margin:2px;display:inline-block">{_esc(kw)}</span>' for kw in missing[:15])
                        st.markdown(f"**Missing:** {kw_html}", unsafe_allow_html=True)
                st.caption("Overall blends keyword match (65%) with best practices (35%)")

            st.markdown("<div style='margin-top:1rem'>", unsafe_allow_html=True)
            for check, passed in result["general_checks"].items():
                icon = "✅" if passed else "⚠️"
                cls  = "pass" if passed else "fail"
                st.markdown(f'<div class="check-item {cls}"><span class="check-icon">{icon}</span>{check}</div>', unsafe_allow_html=True)
            st.markdown("</div></div>", unsafe_allow_html=True)

    if run_kw:
        if not has_resume:
            st.warning("Add a resume first.")
        else:
            with st.spinner("Running AI keyword gap analysis..."):
                try:
                    st.markdown(ai.keyword_gap_analysis(st.session_state.resume_text, st.session_state.jd_text))
                except Exception as e:
                    st.error(str(e))

    if run_rev:
        if not has_resume:
            st.warning("Add a resume first.")
        else:
            with st.spinner("Running AI resume review..."):
                try:
                    st.markdown(ai.general_resume_review(st.session_state.resume_text))
                except Exception as e:
                    st.error(str(e))


# ═══════════════════════════════════════════════════════════════
#  TAB 2 — AI Resume Improver
# ═══════════════════════════════════════════════════════════════
with tab2:
    st.markdown("""
    <div class="section-header">
        <div class="section-icon" style="background:linear-gradient(135deg,rgba(155,93,229,0.2),rgba(247,37,133,0.2))">✨</div>
        <div>
            <div class="section-title">AI Resume Improver</div>
            <div class="section-subtitle">Advanced rewriting with power verbs, quantified impact, PAR format & ATS optimization</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    has_resume = bool(st.session_state.resume_text.strip())
    has_jd     = bool(st.session_state.jd_text.strip())

    # Mode indicator
    if has_jd:
        mode_color, mode_icon, mode_text = "var(--neon-cyan)", "🎯", "Tailoring to your job description from Tab 1"
    elif st.session_state.get("target_keywords", "").strip():
        mode_color, mode_icon, mode_text = "var(--neon-purple)", "🔧", f"Optimizing for: **{st.session_state.target_keywords}**"
    else:
        mode_color, mode_icon, mode_text = "var(--neon-gold)", "✨", "General best-practices improvement (no JD set)"

    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.03);border:1px solid {mode_color}33;border-left:3px solid {mode_color};
         border-radius:var(--radius-sm);padding:0.7rem 1rem;margin-bottom:1rem;font-size:0.88rem;color:{mode_color}">
        {mode_icon} <strong>Mode:</strong> {mode_text}
    </div>
    """, unsafe_allow_html=True)

    c_kw, c_opt = st.columns([2, 1])
    with c_kw:
        st.session_state.target_keywords = st.text_input(
            "Target role / keywords (used only if no JD is set in Tab 1)",
            value=st.session_state.get("target_keywords", ""),
            disabled=has_jd,
            placeholder="e.g. Machine Learning Engineer, Python, AWS, LLMs",
        )

    # Improvement options
    st.markdown("**⚙️ Improvement Options**")
    opt_cols = st.columns(4)
    opt_power_verbs  = opt_cols[0].checkbox("💪 Power Verbs",   value=True)
    opt_quantify     = opt_cols[1].checkbox("📊 Quantify Impact",value=True)
    opt_par          = opt_cols[2].checkbox("🎯 PAR Format",     value=True)
    opt_ats_density  = opt_cols[3].checkbox("🔑 ATS Keywords",   value=True)

    with st.expander("📎 Upload .tex source (preserves your Overleaf design)"):
        tex_file = st.file_uploader("Resume .tex file", type=["tex"], key="tex_upload")
        if tex_file is not None:
            st.session_state.original_tex = tex_file.read().decode("utf-8", errors="ignore")
        if st.session_state.get("original_tex"):
            st.success("✅ Using your uploaded .tex as the base design — output will match your template exactly.")

    improve_col1, improve_col2 = st.columns([1, 1])

    with improve_col1:
        if st.button("✨ Improve My Resume", type="primary", use_container_width=True):
            if not has_resume:
                st.warning("Add a resume in Tab 1 first.")
            else:
                jd = st.session_state.jd_text
                kw = st.session_state.get("target_keywords", "")
                with st.spinner("🔮 AI is rewriting your resume with advanced techniques..."):
                    try:
                        using_tex = bool(st.session_state.get("original_tex"))
                        base_tex  = (
                            st.session_state.original_tex if using_tex
                            else latex_generator.generate_tex(st.session_state.resume_text)
                        )
                        segments = latex_editor.extract_segments(base_tex)

                        if segments:
                            seg_dicts = [{"id": s.id, "text": s.text} for s in segments]
                            edits = ai.improve_latex_segments(seg_dicts, jd, kw)
                            final_tex = latex_editor.apply_edits(base_tex, segments, edits)
                        elif using_tex:
                            final_tex = ai.improve_latex(base_tex, jd, kw)
                        else:
                            final_tex = base_tex

                        st.session_state.edited_tex = final_tex
                        st.session_state.improved_resume = ai.improve_resume(
                            st.session_state.resume_text, jd, kw)
                        st.session_state.used_tex_source = using_tex
                        st.success("✅ Resume improved! Scroll down to preview and download.")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    with improve_col2:
        if has_jd and has_resume:
            if st.button("🎯 Score Job Fit (AI)", use_container_width=True):
                with st.spinner("Calculating job fit..."):
                    try:
                        fit = ai.score_job_fit(st.session_state.resume_text, st.session_state.jd_text)
                        st.session_state.last_fit_score = fit
                    except Exception as e:
                        st.error(str(e))

    # Job Fit display
    if st.session_state.get("last_fit_score"):
        fit = st.session_state.last_fit_score
        score = fit.get("overall_score", 0)
        rec   = fit.get("recommendation", "")
        rec_color = {
            "Strong Apply": "var(--neon-green)",
            "Apply": "var(--neon-cyan)",
            "Apply with Cover Letter": "var(--neon-gold)",
            "Skip": "var(--neon-pink)",
        }.get(rec, "var(--text-secondary)")

        st.markdown(f"""
        <div class="glass-card" style="margin-top:0.8rem">
            <div style="display:flex;align-items:center;gap:1.5rem;margin-bottom:0.8rem">
                <div style="text-align:center;min-width:80px">
                    <div style="font-size:2.5rem;font-weight:900;color:{'var(--neon-green)' if score>=80 else 'var(--neon-cyan)' if score>=65 else 'var(--neon-gold)' if score>=50 else 'var(--neon-pink)'};line-height:1">{score}</div>
                    <div style="font-size:0.65rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em">Fit Score</div>
                </div>
                <div style="flex:1">
                    <div style="font-size:0.95rem;font-weight:700;color:{rec_color};margin-bottom:4px">→ {rec}</div>
                    <div style="font-size:0.82rem;color:var(--text-secondary)">{fit.get('reasoning','')}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        fc1, fc2, fc3, fc4 = st.columns(4)
        for col, label, key in [
            (fc1, "Skills", "skills_match"),
            (fc2, "Experience", "experience_match"),
            (fc3, "Education", "education_match"),
            (fc4, "Culture", "culture_fit"),
        ]:
            val = fit.get(key, 0)
            col.metric(label, f"{val}/100")

        if fit.get("strengths"):
            st.markdown("**✅ Strengths:** " + " · ".join(fit["strengths"]))
        if fit.get("gaps"):
            st.markdown("**⚠️ Gaps:** " + " · ".join(fit["gaps"]))
        st.markdown("</div>", unsafe_allow_html=True)

    # Preview & Downloads
    if st.session_state.get("edited_tex"):
        st.markdown("---")
        st.markdown("**📄 Preview & Download Your Improved Resume**")
        with st.expander("View generated .tex source"):
            st.code(st.session_state.edited_tex, language="latex")

        docx_path = os.path.join(tempfile.gettempdir(), "improved_resume.docx")
        tex_path  = os.path.join(tempfile.gettempdir(), "improved_resume.tex")
        pdf_path  = os.path.join(tempfile.gettempdir(), "improved_resume.pdf")

        Path(tex_path).write_text(st.session_state.edited_tex, encoding="utf-8")
        parser.text_to_docx(st.session_state.improved_resume, docx_path)

        pdf_ready = False
        if latex_editor.pdflatex_available():
            try:
                latex_editor.compile_pdf(st.session_state.edited_tex, pdf_path)
                pdf_ready = True
            except Exception as e:
                st.warning(f"LaTeX→PDF compile failed, falling back to simple PDF. Paste the .tex into Overleaf for the polished version. Error: {e}")
        if not pdf_ready:
            parser.text_to_pdf(st.session_state.improved_resume, pdf_path)

        dl1, dl2, dl3 = st.columns(3)
        with dl1:
            with open(pdf_path, "rb") as f:
                label = "⬇️ Download PDF" + ("  (LaTeX design)" if pdf_ready else "  (simple)")
                st.download_button(label, f, file_name="improved_resume.pdf", use_container_width=True)
        with dl2:
            with open(docx_path, "rb") as f:
                st.download_button("⬇️ Download DOCX", f, file_name="improved_resume.docx", use_container_width=True)
        with dl3:
            with open(tex_path, "rb") as f:
                st.download_button("⬇️ Download .tex (Overleaf)", f, file_name="improved_resume.tex", use_container_width=True)

        if not pdf_ready:
            st.caption("💡 No local LaTeX detected. Install TinyTeX (see README) or paste the .tex into Overleaf for the full polished design.")


# ═══════════════════════════════════════════════════════════════
#  TAB 3 — Cover Letter
# ═══════════════════════════════════════════════════════════════
with tab3:
    st.markdown("""
    <div class="section-header">
        <div class="section-icon" style="background:linear-gradient(135deg,rgba(67,233,123,0.2),rgba(0,207,255,0.2))">📝</div>
        <div>
            <div class="section-title">Cover Letter Generator</div>
            <div class="section-subtitle">Hook-first, cliché-free cover letters tailored to the specific role</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    cc1, cc2 = st.columns(2)
    company = cc1.text_input("Company name", placeholder="e.g. Google, Stripe, OpenAI")
    role    = cc2.text_input("Role title", placeholder="e.g. Senior Software Engineer")

    cl_col1, cl_col2 = st.columns([1, 1])

    with cl_col1:
        if st.button("📝 Generate Cover Letter", type="primary", use_container_width=True):
            if not st.session_state.resume_text or not st.session_state.jd_text:
                st.warning("Add a resume and job description in Tab 1 first.")
            else:
                with st.spinner("✍️ Writing your cover letter..."):
                    try:
                        st.session_state.cover_letter = ai.generate_cover_letter(
                            st.session_state.resume_text, st.session_state.jd_text, company, role)
                        st.success("✅ Cover letter generated!")
                    except Exception as e:
                        st.error(str(e))

    with cl_col2:
        if st.button("💬 LinkedIn Outreach Messages", use_container_width=True):
            if not st.session_state.resume_text or not st.session_state.jd_text:
                st.warning("Add a resume and job description in Tab 1 first.")
            else:
                with st.spinner("Writing LinkedIn messages..."):
                    try:
                        st.session_state.linkedin_msgs = ai.generate_linkedin_message(
                            st.session_state.resume_text, st.session_state.jd_text, company, role)
                    except Exception as e:
                        st.error(str(e))

    if st.session_state.get("cover_letter"):
        st.markdown("**Your Cover Letter:**")
        edited_cl = st.text_area(
            "Edit if needed:",
            value=st.session_state.cover_letter,
            height=350,
            label_visibility="collapsed",
        )
        st.session_state.cover_letter = edited_cl

        # Download cover letter as txt
        st.download_button(
            "⬇️ Download Cover Letter (.txt)",
            st.session_state.cover_letter,
            file_name=f"cover_letter_{company or 'job'}.txt",
            mime="text/plain",
        )

    if st.session_state.get("linkedin_msgs"):
        st.markdown("---")
        st.markdown("**LinkedIn Outreach Messages:**")
        st.markdown(st.session_state.linkedin_msgs)


# ═══════════════════════════════════════════════════════════════
#  TAB 4 — Job Search
# ═══════════════════════════════════════════════════════════════
with tab4:
    st.markdown("""
    <div class="section-header">
        <div class="section-icon" style="background:linear-gradient(135deg,rgba(255,214,10,0.2),rgba(255,149,0,0.2))">🔍</div>
        <div>
            <div class="section-title">Job Search</div>
            <div class="section-subtitle">Searches Remotive, Adzuna, Arbeitnow & Jooble — public APIs, ToS-compliant</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    search_col1, search_col2, search_col3 = st.columns([3, 2, 1])
    q   = search_col1.text_input("Search term", placeholder="e.g. Python backend engineer, ML researcher", label_visibility="collapsed")
    loc = search_col2.text_input("Location", placeholder="Location (optional)", label_visibility="collapsed")

    with search_col3:
        search_clicked = st.button("🔍 Search", type="primary", use_container_width=True)

    if search_clicked and q:
        with st.spinner("🌐 Searching across all job boards..."):
            st.session_state.job_results = jobs.search_all(
                q,
                adzuna_app_id=os.getenv("ADZUNA_APP_ID", ""),
                adzuna_app_key=os.getenv("ADZUNA_APP_KEY", ""),
                jooble_api_key=os.getenv("JOOBLE_API_KEY", ""),
                location=loc,
            )
            st.session_state.selected_jobs = set()

    results = st.session_state.get("job_results", [])

    if not results:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:var(--text-muted)">
            <div style="font-size:3rem;margin-bottom:0.5rem">🔍</div>
            <div style="font-size:1rem;font-weight:600">Search for jobs above to see results</div>
            <div style="font-size:0.8rem;margin-top:0.3rem">Searches Remotive, Adzuna, Arbeitnow, and Jooble simultaneously</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"**{len(results)} positions found**")

        # Select all / deselect all
        sel_col1, sel_col2, sel_col3 = st.columns([1, 1, 4])
        if sel_col1.button("☑️ Select All", use_container_width=True):
            st.session_state.selected_jobs = {r["url"] for r in results}
            st.rerun()
        if sel_col2.button("☐ Deselect All", use_container_width=True):
            st.session_state.selected_jobs = set()
            st.rerun()

        for i, r in enumerate(results):
            source = r.get("source", "")
            badge_class = {
                "Remotive": "badge-remotive",
                "Adzuna": "badge-adzuna",
                "Jooble": "badge-jooble",
                "Arbeitnow": "badge-arbeitnow",
            }.get(source, "badge-arbeitnow")

            rc1, rc2 = st.columns([6, 1])
            with rc1:
                selected = r["url"] in st.session_state.selected_jobs
                checked  = st.checkbox(
                    f"**{r['title']}** — {r['company'] or 'Unknown'}  •  {r['location'] or ''}",
                    value=selected,
                    key=f"sel_{i}_{r['url'][:30]}",
                )
                if checked:
                    st.session_state.selected_jobs.add(r["url"])
                else:
                    st.session_state.selected_jobs.discard(r["url"])

                st.markdown(
                    f'<span class="platform-badge {badge_class}">{_esc(source)}</span>'
                    f' <a href="{_safe_url(r["url"])}" target="_blank" rel="noopener noreferrer" style="color:var(--neon-cyan);font-size:0.78rem;text-decoration:none">Open listing ↗</a>',
                    unsafe_allow_html=True
                )

            with rc2:
                if st.button("➕ Track", key=f"add_{i}", use_container_width=True):
                    tracker.add_application(r["company"] or "Unknown", r["title"], r["url"])
                    st.success("Added to tracker!")

            # AI Fit score
            if has_resume := bool(st.session_state.resume_text.strip()):
                if st.session_state.jd_text and r["url"] in st.session_state.get("fit_scores", {}):
                    fit = st.session_state.fit_scores[r["url"]]
                    score = fit.get("overall_score", 0)
                    color = "var(--neon-green)" if score >= 80 else "var(--neon-cyan)" if score >= 65 else "var(--neon-gold)" if score >= 50 else "var(--neon-pink)"
                    st.markdown(f'<span style="font-size:0.75rem;color:{color}">Fit: {score}/100 · {_esc(fit.get("recommendation",""))}</span>', unsafe_allow_html=True)

            st.markdown("<hr style='margin:0.4rem 0'>", unsafe_allow_html=True)

        # Batch track selected
        if st.session_state.selected_jobs:
            n_selected = len(st.session_state.selected_jobs)
            st.info(f"**{n_selected} jobs selected** — go to the **🤖 Auto-Apply** tab to apply!")


# ═══════════════════════════════════════════════════════════════
#  TAB 5 — Auto-Apply
# ═══════════════════════════════════════════════════════════════
with tab5:
    st.markdown("""
    <div class="section-header">
        <div class="section-icon" style="background:linear-gradient(135deg,rgba(247,37,133,0.2),rgba(155,93,229,0.2))">🤖</div>
        <div>
            <div class="section-title">Auto-Apply Automation</div>
            <div class="section-subtitle">LinkedIn Easy Apply · Indeed Quick Apply · Greenhouse · Lever · Generic forms</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Playwright availability check
    playwright_ok = _is_playwright_available()
    if not playwright_ok:
        st.markdown("""
        <div style="background:rgba(255,214,10,0.08);border:1px solid rgba(255,214,10,0.3);border-left:3px solid var(--neon-gold);border-radius:var(--radius-sm);padding:1rem;margin-bottom:1rem">
            <div style="font-size:0.9rem;font-weight:700;color:var(--neon-gold);margin-bottom:0.4rem">⚠️ Playwright Not Installed</div>
            <div style="font-size:0.82rem;color:var(--text-secondary)">Auto-apply requires Playwright. Install it with:</div>
            <code style="display:block;margin-top:0.5rem;background:rgba(0,0,0,0.3);padding:0.5rem;border-radius:6px;color:var(--neon-cyan)">pip install playwright && playwright install chromium</code>
            <div style="font-size:0.78rem;color:var(--text-muted);margin-top:0.4rem">You can still use all other features without Playwright.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(247,37,133,0.06);border:1px solid rgba(247,37,133,0.2);border-radius:var(--radius-sm);padding:0.8rem 1rem;margin-bottom:1rem;font-size:0.82rem;color:var(--text-secondary)">
        <strong style="color:var(--neon-pink)">⚠️ Important:</strong> Auto-apply works with Easy Apply / Quick Apply features.
        It does NOT bypass paywalls or violate terms of service. You must provide your credentials below.
        Always review applications before batch-applying.
    </div>
    """, unsafe_allow_html=True)

    # Configuration
    with st.expander("⚙️ Credentials & Configuration", expanded=not playwright_ok):
        cfg_col1, cfg_col2 = st.columns(2)

        with cfg_col1:
            st.markdown("**🔵 LinkedIn**")
            li_email = st.text_input("LinkedIn Email", key="li_email",
                                      value=os.getenv("LINKEDIN_EMAIL", ""),
                                      placeholder="your@email.com")
            li_pass  = st.text_input("LinkedIn Password", type="password", key="li_pass",
                                      value=os.getenv("LINKEDIN_PASSWORD", ""),
                                      placeholder="••••••••")

        with cfg_col2:
            st.markdown("**🟡 Indeed**")
            in_email = st.text_input("Indeed Email", key="in_email",
                                      value=os.getenv("INDEED_EMAIL", ""),
                                      placeholder="your@email.com")
            in_pass  = st.text_input("Indeed Password", type="password", key="in_pass",
                                      value=os.getenv("INDEED_PASSWORD", ""),
                                      placeholder="••••••••")

        st.markdown("**👤 Personal Info** (for form auto-fill)")
        pi_col1, pi_col2, pi_col3, pi_col4 = st.columns(4)
        first_name = pi_col1.text_input("First Name", value=os.getenv("FIRST_NAME", ""), key="first_name_input")
        last_name  = pi_col2.text_input("Last Name", value=os.getenv("LAST_NAME", ""), key="last_name_input")
        phone      = pi_col3.text_input("Phone", value=os.getenv("PHONE_NUMBER", ""), key="phone_input")
        apply_email= pi_col4.text_input("Apply Email", value=os.getenv("APPLY_EMAIL", ""), key="apply_email_input")

        headless = st.checkbox("Run headless (no browser window)", value=True)

        # Resume file for upload
        st.markdown("**📄 Resume File for Upload** (for file-picker fields)")
        auto_resume = st.file_uploader("Upload your resume (PDF for auto-apply forms)", type=["pdf"], key="auto_resume")
        resume_path = ""
        if auto_resume:
            _apply_dir = Path(tempfile.gettempdir()) / "gamehire"
            _apply_dir.mkdir(exist_ok=True)
            resume_path = str(_apply_dir / "auto_apply_resume.pdf")  # overwritten each time, never accumulates
            Path(resume_path).write_bytes(auto_resume.getvalue())
            st.success(f"✅ Resume ready: {auto_resume.name}")

    # What to apply to
    st.markdown("---")
    st.markdown("**📋 Applications Queue**")

    selected_from_search = list(st.session_state.selected_jobs)
    results_map = {r["url"]: r for r in st.session_state.get("job_results", [])}

    apply_mode = st.radio(
        "Apply to:",
        ["Selected jobs from search", "Custom URLs"],
        horizontal=True,
    )

    custom_jobs = []
    if apply_mode == "Custom URLs":
        custom_text = st.text_area(
            "Enter job URLs (one per line, format: URL | Company | Role)",
            placeholder="https://linkedin.com/jobs/... | Google | Software Engineer\nhttps://greenhouse.io/... | Stripe | Backend Engineer",
            height=120,
        )
        if custom_text.strip():
            for line in custom_text.strip().splitlines():
                parts = [p.strip() for p in line.split("|")]
                url     = parts[0] if len(parts) > 0 else ""
                company = parts[1] if len(parts) > 1 else "Unknown"
                role    = parts[2] if len(parts) > 2 else "Unknown"
                if url.startswith("http"):
                    custom_jobs.append({"url": url, "company": company, "role": role})

    # Queue display
    queue_jobs = []
    if apply_mode == "Selected jobs from search":
        queue_jobs = [
            {
                "url": url,
                "company": results_map.get(url, {}).get("company", "Unknown"),
                "role": results_map.get(url, {}).get("title", "Unknown"),
            }
            for url in selected_from_search
        ]
    else:
        queue_jobs = custom_jobs

    if queue_jobs:
        st.markdown(f"**{len(queue_jobs)} job(s) in queue:**")
        for job in queue_jobs[:10]:
            st.markdown(
                f'<div class="job-card"><div class="job-title">{_esc(job["role"])}</div>'
                f'<div class="job-company">{_esc(job["company"])}</div>'
                f'<div class="job-meta"><a href="{_safe_url(job["url"])}" target="_blank" rel="noopener noreferrer" style="color:var(--text-muted);font-size:0.72rem">{_esc(job["url"][:70])}...</a></div></div>',
                unsafe_allow_html=True
            )
        if len(queue_jobs) > 10:
            st.caption(f"... and {len(queue_jobs)-10} more")
    else:
        st.info("No jobs in queue. Select jobs in the Job Search tab or enter custom URLs above.")

    # Apply button
    st.markdown("---")
    apply_col1, apply_col2 = st.columns([1, 2])

    with apply_col1:
        if st.button(
            f"🚀 Auto-Apply to {len(queue_jobs)} Job(s)" if queue_jobs else "🚀 Auto-Apply",
            type="primary",
            use_container_width=True,
            disabled=not queue_jobs or not playwright_ok,
        ):
            if not queue_jobs:
                st.warning("No jobs in queue.")
            elif not playwright_ok:
                st.error("Playwright not installed.")
            else:
                # Build config
                config = ApplyConfig(
                    resume_path=resume_path,
                    cover_letter_text=st.session_state.get("cover_letter", ""),
                    linkedin_email=li_email,
                    linkedin_password=li_pass,
                    indeed_email=in_email,
                    indeed_password=in_pass,
                    headless=headless,
                )

                # Store personal info in env for applier
                os.environ["FIRST_NAME"]   = first_name
                os.environ["LAST_NAME"]    = last_name
                os.environ["PHONE_NUMBER"] = phone
                os.environ["APPLY_EMAIL"]  = apply_email

                progress_placeholder = st.empty()
                log_placeholder      = st.empty()
                apply_log = []

                def progress_cb(msg):
                    apply_log.append(msg)
                    progress_placeholder.markdown(f"**{msg}**")

                progress_placeholder.markdown("**🚀 Starting auto-apply...**")

                results_list = batch_apply(queue_jobs, config, progress_cb, delay_between=2.0)
                st.session_state.apply_log = results_list

                # Summarize
                successes = sum(1 for r in results_list if r.success)
                failures  = len(results_list) - successes
                progress_placeholder.empty()

                if successes > 0:
                    st.success(f"✅ Applied to {successes}/{len(results_list)} jobs!")
                if failures > 0:
                    st.warning(f"⚠️ {failures} application(s) could not be automated — added to tracker as 'Saved' for manual follow-up.")

    with apply_col2:
        if st.session_state.get("apply_log"):
            st.markdown("**📋 Last Apply Run Results:**")
            for res in st.session_state.apply_log:
                icon  = "✅" if res.success else "❌"
                color = "var(--neon-green)" if res.success else "var(--neon-pink)"
                st.markdown(
                    f'<div style="border-left:3px solid {color};padding:6px 12px;margin:4px 0;border-radius:0 var(--radius-sm) var(--radius-sm) 0;background:rgba(255,255,255,0.02);font-size:0.82rem">'
                    f'{icon} <strong style="color:{color}">{_esc(res.role)}</strong> @ {_esc(res.company)}<br>'
                    f'<span style="color:var(--text-muted)">{_esc(res.message)}</span></div>',
                    unsafe_allow_html=True
                )


# ═══════════════════════════════════════════════════════════════
#  TAB 6 — Interview Prep
# ═══════════════════════════════════════════════════════════════
with tab6:
    st.markdown("""
    <div class="section-header">
        <div class="section-icon" style="background:linear-gradient(135deg,rgba(155,93,229,0.2),rgba(0,207,255,0.2))">🎙️</div>
        <div>
            <div class="section-title">Interview Prep</div>
            <div class="section-subtitle">AI-generated questions, STAR feedback & curveball prep</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🎙️ Generate Interview Questions & Strategy", type="primary"):
        if not st.session_state.resume_text or not st.session_state.jd_text:
            st.warning("Add a resume and job description in Tab 1 first.")
        else:
            with st.spinner("🤔 Thinking like a hiring manager..."):
                try:
                    result = ai.generate_interview_questions(
                        st.session_state.resume_text, st.session_state.jd_text)
                    st.session_state.interview_questions = result
                except Exception as e:
                    st.error(str(e))

    if st.session_state.get("interview_questions"):
        st.markdown(st.session_state.interview_questions)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.9rem;font-weight:700;color:var(--text-primary);margin-bottom:0.6rem">
        💬 Practice Answer Coaching
    </div>
    """, unsafe_allow_html=True)

    q_practice = st.text_input("Interview question to practice",
                                placeholder="e.g. Tell me about a time you led a difficult project under pressure")
    a_practice = st.text_area("Your answer", height=130,
                               placeholder="Write your answer here — I'll give you STAR feedback...")

    if st.button("🎯 Get Coaching Feedback"):
        if not q_practice or not a_practice:
            st.warning("Enter a question and your answer.")
        else:
            with st.spinner("Coaching..."):
                try:
                    feedback = ai.mock_interview_feedback(
                        q_practice, a_practice, st.session_state.resume_text)
                    st.markdown(feedback)
                except Exception as e:
                    st.error(str(e))


# ═══════════════════════════════════════════════════════════════
#  TAB 7 — Tracker
# ═══════════════════════════════════════════════════════════════
with tab7:
    st.markdown("""
    <div class="section-header">
        <div class="section-icon" style="background:linear-gradient(135deg,rgba(67,233,123,0.2),rgba(0,207,255,0.2))">📊</div>
        <div>
            <div class="section-title">Application Tracker</div>
            <div class="section-subtitle">Track every application · status pipeline · notes · auto-apply log</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Pipeline funnel
    st.markdown(f"""
    <div class="pipeline">
        <div class="pipeline-stage">
            <div class="pipeline-count" style="color:#8fa3c8">{stats['saved']}</div>
            <div class="pipeline-label">Saved</div>
        </div>
        <div class="pipeline-stage">
            <div class="pipeline-count" style="color:var(--neon-cyan)">{stats['applied']}</div>
            <div class="pipeline-label">Applied</div>
        </div>
        <div class="pipeline-stage">
            <div class="pipeline-count" style="color:var(--neon-purple)">{stats['interviewing']}</div>
            <div class="pipeline-label">Interview</div>
        </div>
        <div class="pipeline-stage">
            <div class="pipeline-count" style="color:var(--neon-green)">{stats['offer']}</div>
            <div class="pipeline-label">Offer</div>
        </div>
        <div class="pipeline-stage">
            <div class="pipeline-count" style="color:var(--neon-pink)">{stats['rejected']}</div>
            <div class="pipeline-label">Rejected</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Manual add
    with st.expander("➕ Add Application Manually"):
        m1, m2, m3, m4 = st.columns([2, 2, 3, 1])
        mc = m1.text_input("Company", key="manual_company")
        mr = m2.text_input("Role",    key="manual_role")
        mu = m3.text_input("URL",     key="manual_url")
        mn = st.text_input("Notes (optional)", key="manual_notes")
        if m4.button("Add", use_container_width=True):
            if mc and mr:
                tracker.add_application(mc, mr, mu, notes=mn)
                st.success("✅ Added!")
                st.rerun()
            else:
                st.warning("Company and Role are required.")

    # Filter
    filter_col1, filter_col2 = st.columns([2, 1])
    filter_status = filter_col1.selectbox(
        "Filter by status",
        ["All", "Saved", "Applied", "Interviewing", "Offer", "Rejected"],
        label_visibility="collapsed",
    )
    sort_by = filter_col2.selectbox(
        "Sort",
        ["Newest first", "Oldest first"],
        label_visibility="collapsed",
    )

    apps = tracker.list_applications()
    if sort_by == "Oldest first":
        apps = list(reversed(apps))
    if filter_status != "All":
        apps = [a for a in apps if a["status"] == filter_status]

    statuses = ["Saved", "Applied", "Interviewing", "Offer", "Rejected"]

    if not apps:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:var(--text-muted)">
            <div style="font-size:3rem;margin-bottom:0.5rem">📋</div>
            <div style="font-size:1rem;font-weight:600">No applications tracked yet</div>
            <div style="font-size:0.8rem;margin-top:0.3rem">Add applications manually above or use Job Search → Auto-Apply</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for a in apps:
            status_colors = {
                "Saved": "#8fa3c8", "Applied": "#00cfff", "Interviewing": "#9b5de5",
                "Offer": "#43e97b", "Rejected": "#f72585"
            }
            s_color = status_colors.get(a["status"], "#8fa3c8")

            with st.container():
                cols = st.columns([3, 2, 2, 2, 1])

                with cols[0]:
                    auto_badge = ' <span style="font-size:0.65rem;color:var(--neon-gold);background:rgba(255,214,10,0.1);padding:1px 6px;border-radius:4px">🤖 AUTO</span>' if a.get("auto_applied") else ""
                    st.markdown(
                        f"**{_esc(a['company'])}**{auto_badge}  \n"
                        f'<span style="font-size:0.82rem;color:var(--text-secondary)">{_esc(a["role"])}</span>',
                        unsafe_allow_html=True
                    )

                with cols[1]:
                    if a.get("url"):
                        st.markdown(f'<a href="{_safe_url(a["url"])}" target="_blank" rel="noopener noreferrer" style="color:var(--neon-cyan);font-size:0.78rem">Open listing ↗</a>', unsafe_allow_html=True)
                    st.markdown(f'<span style="font-size:0.72rem;color:var(--text-muted)">{a.get("date_applied","")}</span>', unsafe_allow_html=True)

                with cols[2]:
                    current_index = statuses.index(a["status"]) if a["status"] in statuses else 0
                    new_status = st.selectbox(
                        "Status",
                        statuses,
                        index=current_index,
                        key=f"status_{a['id']}",
                        label_visibility="collapsed",
                    )
                    if new_status != a["status"]:
                        tracker.update_status(a["id"], new_status)
                        st.rerun()

                with cols[3]:
                    notes_val = st.text_input(
                        "Notes",
                        value=a.get("notes", "") or "",
                        key=f"notes_{a['id']}",
                        placeholder="Add notes...",
                        label_visibility="collapsed",
                    )
                    if notes_val != (a.get("notes") or ""):
                        tracker.update_notes(a["id"], notes_val)

                with cols[4]:
                    if st.button("🗑", key=f"del_{a['id']}", use_container_width=True):
                        tracker.delete_application(a["id"])
                        st.rerun()

                st.markdown("<hr style='margin:0.3rem 0'>", unsafe_allow_html=True)

    # Export
    if apps:
        import csv, io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["id","company","role","url","status","date_applied","notes","auto_applied","platform","fit_score"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(apps)
        st.download_button(
            "⬇️ Export All as CSV",
            output.getvalue(),
            file_name="job_applications.csv",
            mime="text/csv",
        )

