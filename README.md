# Decision Advisor

An AI-powered decision intelligence platform that helps individuals and professionals make better decisions by providing comprehensive analysis from three perspectives: **market conditions**, **risk assessment**, and **cognitive psychology**.

## The Problem

Making important decisions — career changes, business investments, personal moves — is hard. People typically rely on:
- **Gut feeling** alone, which is prone to cognitive biases
- **One-dimensional analysis** (e.g., only looking at financial risk)
- **Inconsistent frameworks** that vary from decision to decision

This leads to decision paralysis, regret, and suboptimal outcomes.

## The Solution

Decision Advisor uses **multiple AI agents** to analyze every decision from three angles simultaneously:

1. **Market Agent** — Evaluates market conditions, opportunities, threats, and timing
2. **Risk Agent** — Scores risk (1–10), identifies best/worst cases, and provides actionable recommendations
3. **Psychology Agent** — Detects cognitive biases (anchoring, confirmation bias, etc.) and assesses alignment with your stated priorities

A single orchestrator consolidates all three analyses into a unified verdict with a clear risk signal (Low / Moderate / High).

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Browser (SPA)                     │
│  index.html — Form → fetch /decide → Render Report  │
└──────────────────────┬──────────────────────────────┘
                       │ POST /decide
                       ▼
┌─────────────────────────────────────────────────────┐
│                 FastAPI Backend                       │
│  main.py — Rate Limiting · Input Sanitization ·      │
│            Secure Error Handling                     │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              Orchestrator Agent                       │
│  orchestrator.py — powered by Groq (LLaMA 3.3 70B)   │
│  • Builds consolidated prompt                        │
│  • Calls Market / Risk / Psychology sub-agents       │
│  • Parses structured JSON responses                  │
│  • Synthesizes a unified verdict                     │
└─────────────────────────────────────────────────────┘
```

### Agent Pipeline

```
User Input ──→ Orchestrator ──→ Groq (LLaMA 3.3 70B)
                    │
                    ├── MARKET analysis      (opportunities, threats, timing)
                    ├── RISK analysis        (score, best/worst case, recommendation)
                    └── PSYCHOLOGY analysis  (biases, alignment, gut check)
                    │
                    ▼
              Unified Verdict (JSON + human-readable summary)
```

### Request Schema (`POST /decide`)

```json
{
  "decision": "string — the decision being considered",
  "risk_tolerance": "string — low / moderate / high",
  "priority": "string — what matters most to the user",
  "timeline": "string — when the decision needs to be made",
  "past_decisions": "string — relevant context from past choices"
}
```

## Security Features

- **Rate Limiting** — 5 requests per minute per IP via `slowapi`
- **Input Sanitization** — Regex-based prompt injection detection + 2000-char field truncation, enforced via a Pydantic field validator
- **Secure Error Handling** — Generic messages returned to clients; full tracebacks logged server-side with a correlation ID for debugging

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Uvicorn |
| AI (sub-agents & orchestrator) | Groq LLaMA 3.3 70B via the `groq` SDK |
| Frontend | Vanilla HTML/CSS/JS (single-page) |
| Rate Limiting | `slowapi` |
| Config | `python-dotenv` |

## Setup & Installation

### Prerequisites

- Python 3.10+
- API key for [Groq](https://console.groq.com/keys) (LLaMA)

### 1. Clone & create virtual environment

```bash
git clone <repo-url>
cd decision-advisor-capstone
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your-groq-api-key
```

### 4. Run the server

```bash
python -m uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

## Project Structure

```
decision-advisor-capstone/
├── main.py                      # FastAPI app, routes, security wiring
├── security.py                  # Rate limiting, sanitization, error handling
├── index.html                   # Single-page frontend (HTML/CSS/JS)
├── requirements.txt             # Python dependencies
├── .env                         # API keys (git-ignored)
├── .gitignore
└── agents/
    ├── __init__.py
    ├── orchestrator.py          # Central AI pipeline (Groq)
    ├── market_agent.py          # Market analysis sub-agent
    ├── risk_agent.py            # Risk assessment sub-agent
    └── psychology_agent.py      # Cognitive bias detection sub-agent
```

## How It Works

1. **User submits a decision** via the form (what, risk tolerance, priority, timeline, past context)
2. **FastAPI validates and sanitizes** the input and applies rate limiting
3. **Orchestrator** constructs a consolidated prompt and dispatches it to the Market, Risk, and Psychology sub-agents via Groq
4. **Orchestrator builds a verdict** — a human-readable summary with a risk signal (Low / Moderate / High)
5. **Frontend renders the report** in four cards: Market Analysis, Risk Assessment, Psychology Check, and Final Verdict