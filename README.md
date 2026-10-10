# ⚡ GameHire

**AI-Powered Job Search Copilot** — Resume optimizer, ATS scorer, cover letter writer, interview coach, and auto-apply automation. Runs 100% locally by default via Ollama — nothing leaves your machine.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.38+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20AI-black?logo=ollama)](https://ollama.ai)
[![Playwright](https://img.shields.io/badge/Playwright-Auto--Apply-45ba4b?logo=playwright)](https://playwright.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 👨‍💻 Developer

**Sahil Rafiq**

* GitHub: [@sahilrafiq](https://github.com/sahilrafiq)
* LinkedIn: [sahil-rafiq](https://www.linkedin.com/in/sahil-rafiq/)

---

## 🎯 What Is GameHire?

GameHire is a locally-running, privacy-first AI assistant for every stage of your job search:

| Stage | What GameHire Does |
|---|---|
| 📄 **Resume** | Uploads PDF/DOCX/TXT, extracts text, edits in place |
| ⚡ **ATS Scoring** | Rule-based + AI scoring against a specific JD or general best practices |
| ✨ **AI Rewrite** | Rewrites with power verbs, PAR format, quantified impact — via Ollama or Claude |
| 📝 **Cover Letter** | Hook-first, cliché-free letters tailored to the exact role |
| 💬 **LinkedIn Outreach** | 300-char connection note + full InMail message |
| 🔍 **Job Search** | Searches Remotive, Adzuna, Arbeitnow, Jooble simultaneously |
| 🤖 **Auto-Apply** | LinkedIn Easy Apply, Indeed Quick Apply, Greenhouse, Lever automation |
| 🎙️ **Interview Prep** | Generates 8 role-specific questions + STAR coaching feedback |
| 📊 **Tracker** | Local SQLite pipeline: Saved → Applied → Interviewing → Offer |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GameHire (Streamlit UI)                       │
│           7 tabs: Resume·ATS·Improver·Cover·Search·Apply·Track  │
└──────────┬──────────────────────────────────────────────────────┘
           │
     ┌─────┴──────────────────────────────────────────────┐
     │                  core/ modules                      │
     ├──────────────┬───────────────┬──────────────────────┤
     │  ai.py       │  ats.py       │  jobs.py             │
     │  • Ollama    │  • Rule-based │  • Remotive API      │
     │  • Anthropic │    scoring    │  • Adzuna API        │
     │  • 8 AI fns  │  • Keyword    │  • Arbeitnow API     │
     │              │    matcher    │  • Jooble API        │
     ├──────────────┼───────────────┼──────────────────────┤
     │  applier.py  │  tracker.py   │  parser.py           │
     │  • Playwright│  • SQLite DB  │  • PDF (pdfplumber)  │
     │  • LinkedIn  │  • Pipeline   │  • DOCX (python-docx)│
     │  • Indeed    │    stats      │  • Text→DOCX/PDF     │
     │  • Greenhouse│               │                      │
     │  • Lever     │  latex_*.py   │                      │
     │  • Generic   │  • LaTeX edit │                      │
     └──────────────┴───────────────┴──────────────────────┘
           │
     ┌─────┴──────────────────────────────────────┐
     │              AI Backends                    │
     │  Ollama (local) ◄──── default, free        │
     │  Anthropic Claude ◄── optional, cloud      │
     └────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Clone & set up environment

```bash
git clone https://github.com/sahilrafiq/gamehire-ai.git
cd gamehire-ai

python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure `.env`

```bash
cp .env.example .env
```

Open `.env` and fill in your values (see [Configuration](#-configuration) below).

### 3. Start Ollama (default local AI)

```bash
# Install Ollama from https://ollama.ai, then:
ollama serve
ollama pull qwen2.5:7b   # recommended starting model if you have 8-16 GB of Ram
```

### 4. Run GameHire

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser. 🎉

---

## 🤖 Auto-Apply Setup (Optional)

Auto-apply uses Playwright to automate LinkedIn Easy Apply, Indeed Quick Apply, Greenhouse, and Lever forms.

IMPORTANT:
  * This only works with jobs that have "Easy Apply" / "Quick Apply" features.
    It does NOT bypass login walls you must provide credentials in .env.
  * Automating LinkedIn/Indeed logins and submissions may violate their Terms
    of Service and can get your account restricted. Use at your own risk.
  * Required questions it can't answer are NOT guessed the run stops and
    the job is saved to your tracker for manual completion.
  * A job only counts as "applied" if a confirmation message is detected.

```bash
pip install playwright
playwright install chromium
```

Then add your credentials to `.env`:

```env
LINKEDIN_EMAIL=your@email.com
LINKEDIN_PASSWORD=yourpassword
INDEED_EMAIL=your@email.com
INDEED_PASSWORD=yourpassword
FIRST_NAME=Your
LAST_NAME=Name
PHONE_NUMBER=+1234567890
APPLY_EMAIL=your@email.com
```

> **Tip:** Uncheck "Run headless" on your first run to watch the browser and verify it's working correctly before enabling headless mode.

---

## 📄 LaTeX / Overleaf Resume (Optional)

To preserve your exact Overleaf design when improving your resume:

1. Export your resume `.tex` from Overleaf
2. Upload it in the **✨ AI Improver** tab
3. GameHire edits only the prose (bullets, summary) — never the LaTeX commands
4. Download the compiled `.pdf` or paste the `.tex` back into Overleaf

For local PDF compilation, install TinyTeX:

```bash
# Windows (run as Administrator)
install-tinytex.bat
```

---

## ⚙️ Configuration

All settings live in `.env`. Copy from `.env.example`:

| Variable | Default | Description |
|---|---|---|
| `AI_PROVIDER` | `ollama` | `ollama` (local, free) or `anthropic` (Claude API) |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Any model you've pulled with `ollama pull` |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server address |
| `ANTHROPIC_API_KEY` | — | Get at [console.anthropic.com](https://console.anthropic.com) |
| `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | Claude model used when `AI_PROVIDER=anthropic` (requires `pip install anthropic`) |
| `OLLAMA_NUM_CTX` | `8192` | Ollama context window; raise for very long resumes/job descriptions |
| `ADZUNA_COUNTRY` | `us` | Country code for Adzuna job search (`us`, `gb`, `in`, `ca`, ...) |
| `ADZUNA_APP_ID` | — | Free at [developer.adzuna.com](https://developer.adzuna.com) |
| `ADZUNA_APP_KEY` | — | Same Adzuna registration |
| `JOOBLE_API_KEY` | — | Free at [jooble.org/api/about](https://jooble.org/api/about) |
| `LINKEDIN_EMAIL` | — | For auto-apply automation |
| `LINKEDIN_PASSWORD` | — | For auto-apply automation |
| `INDEED_EMAIL` | — | For auto-apply automation |
| `INDEED_PASSWORD` | — | For auto-apply automation |

> **Job search works without any API keys** — Remotive and Arbeitnow require no keys and return remote jobs by default.

---

## 🧠 AI Model Recommendations

| Hardware | Recommended Model | Quality |
|---|---|---|
| 4 GB RAM | `qwen2.5:3b` or `phi3:mini` | Good |
| 8 GB RAM | `qwen2.5:7b` *(default)* | Very Good |
| 16 GB RAM | `qwen2.5:14b` or `mistral:7b` | Excellent |
| Cloud (no GPU) | `AI_PROVIDER=anthropic` → Claude Sonnet | Best |

---

## 🗂️ Project Structure

```
gamehire-ai/
├── app.py                  # Streamlit UI — all 7 tabs
├── core/
│   ├── ai.py               # AI backend (Ollama / Anthropic)
│   ├── ats.py              # Rule-based ATS & keyword scorer
│   ├── jobs.py             # Job search API aggregator
│   ├── applier.py          # Playwright auto-apply automation
│   ├── tracker.py          # SQLite application tracker
│   ├── parser.py           # Resume parsing (PDF/DOCX/TXT)
│   ├── latex_editor.py     # LaTeX segment editor
│   └── latex_generator.py  # Resume → LaTeX converter
├── applications.db         # Local SQLite DB (auto-created)
├── requirements.txt
├── .env.example
└── install-tinytex.bat     # TinyTeX installer (Windows)
```

---

## 🔍 Job Search Sources

| Source | API Key Required | Job Types |
|---|---|---|
| [Remotive](https://remotive.com) | ❌ No | Remote tech jobs |
| [Arbeitnow](https://arbeitnow.com) | ❌ No | Remote + EU tech |
| [Adzuna](https://developer.adzuna.com) | ✅ Free tier | All types, global |
| [Jooble](https://jooble.org/api/about) | ✅ Free tier | Meta-aggregator |

---

## 🤖 Auto-Apply Platform Support

| Platform | Method | Notes |
|---|---|---|
| LinkedIn | Easy Apply modal | Multi-step, handles file upload |
| Indeed | Quick Apply | Session-based login |
| Greenhouse | Direct form | File upload + text fields |
| Lever | Direct form | File upload + text fields |
| Generic | Best-effort | Name/email/phone/resume auto-fill |

> Auto-apply only works with Easy Apply / Quick Apply features. It does **not** bypass login walls or scrape protected content.

---

## 📦 Dependencies

```
streamlit>=1.38       # UI framework
ollama>=0.3.0         # Local AI (Ollama client)
pdfplumber>=0.11      # PDF text extraction
python-docx>=1.1      # DOCX read/write
reportlab>=4.0        # PDF generation (no LibreOffice needed)
requests>=2.32        # Job search API calls
python-dotenv>=1.0    # .env loading

# Optional
anthropic>=0.34       # Claude API (set AI_PROVIDER=anthropic)
playwright>=1.40      # Auto-apply automation
```

---

## 🛡️ Privacy & Security

- **All AI runs locally by default** — your resume never leaves your machine unless you set `AI_PROVIDER=anthropic`
- **Credentials stay in `.env`** — never committed to git (`.gitignore` covers it)
- **SQLite tracker is local** — `applications.db` stays on your machine
- **Auto-apply is transparent** — you can watch the browser window by unchecking "headless"

---

## 📝 License

MIT — see [LICENSE](LICENSE)

---

*Built with ❤️ by [Sahil Rafiq](https://github.com/sahilrafiq)*
