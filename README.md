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
                       │ (X-API-Key header)
                       ▼
┌─────────────────────────────────────────────────────┐
│                 FastAPI Backend                       │
│  main.py — Rate Limiting · Auth · Input Sanitization │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              Orchestrator Agent                       │
│  orchestrator.py — Gemini 3.5 Flash via google-genai │
│  • Builds consolidated prompt                        │
│  • Parses structured JSON response                   │
│  • Retries on rate limits (429) with exponential backoff │
│  • Synthesizes verdict from all three analyses       │
└─────────────────────────────────────────────────────┘
```

### Agent Pipeline

```
User Input ──→ Orchestrator ──→ Gemini 3.5 Flash
                    │
                    ├── MARKET analysis  (opportunities, threats, timing)
                    ├── RISK analysis    (score, best/worst case, recommendation)
                    └── PSYCHOLOGY analysis (biases, alignment, gut check)
                    │
                    ▼
              Unified Verdict (JSON + human-readable summary)
```

### API Design

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/` | GET | Serves the single-page frontend | — |
| `/decide` | POST | Runs the full analysis pipeline | X-API-Key header |

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
- **Input Sanitization** — Regex-based prompt injection detection + 2000-char field truncation
- **Secure Error Handling** — Generic messages to clients, full tracebacks logged server-side

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Uvicorn |
| AI (Orchestrator) | Google Gemini 3.5 Flash via `google-genai` |
| AI (Sub-agents) | Groq LLaMA 3.3 70B via `groq` |
| Frontend | Vanilla HTML/CSS/JS (single-page) |
| Rate Limiting | slowapi |
| Config | python-dotenv |

## Setup & Installation

### Prerequisites

- Python 3.10+
- API keys for:
  - [Google AI Studio](https://aistudio.google.com/apikey) (Gemini)
  - [Groq](https://console.groq.com/keys) (LLaMA)

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
GEMINI_API_KEY=your-google-gemini-api-key
GROQ_API_KEY=your-groq-api-key
API_KEY=your-chosen-api-key-for-auth
```

> **Note:** If `API_KEY` is omitted, authentication is disabled (development mode).

### 4. Run the server

```bash
python -m uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

## Project Structure

```
decision-advisor-capstone/
├── main.py                      # FastAPI app, routes, security middleware
├── index.html                   # Single-page frontend (HTML/CSS/JS)
├── requirements.txt             # Python dependencies
├── .env                         # API keys (git-ignored)
├── .gitignore
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py          # Central AI pipeline (Gemini)
│   ├── groq_client.py           # Groq API client initialization
│   ├── market_agent.py          # Market analysis sub-agent
│   ├── risk_agent.py            # Risk assessment sub-agent
│   └── psychology_agent.py      # Cognitive bias detection sub-agent
└── tools/
    └── search_tool.py           # Google Search grounding tool
```

## How It Works

1. **User submits a decision** via the form (what, risk tolerance, priority, timeline, past context)
2. **FastAPI validates and sanitizes** the input, checks the API key, and applies rate limits
3. **Orchestrator** constructs a consolidated prompt and sends it to Gemini 3.5 Flash
4. **Gemini returns structured JSON** with market, risk, and psychology analyses
5. **Orchestrator builds a verdict** — a human-readable summary with a risk signal (Low/Moderate/High)
6. **Frontend renders the report** in four cards: Market Analysis, Risk Assessment, Psychology Check, and Final Verdict

