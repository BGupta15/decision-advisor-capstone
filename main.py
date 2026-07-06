"""
Decision Advisor — FastAPI Backend
GET  /       → serves index.html
POST /decide → runs the orchestrator and returns the merged report
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # Load GEMINI_API_KEY from .env before anything else

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, field_validator
from slowapi.middleware import SlowAPIMiddleware

from agents.orchestrator import run_orchestrator
from security import (
    RATE_LIMIT,
    limiter,
    logger,
    sanitize_text,
    setup_error_handling,
    setup_rate_limiting,
)

app = FastAPI(title="Decision Advisor", version="1.0.0")

# ── Security wiring ─────────────────────────────────────────────────────────
setup_rate_limiting(app)
app.add_middleware(SlowAPIMiddleware)
setup_error_handling(app)


# ── Request schema ───────────────────────────────────────────────────────
class DecisionRequest(BaseModel):
    decision: str
    risk_tolerance: str
    priority: str
    timeline: str
    past_decisions: str

    @field_validator(
        "decision", "risk_tolerance", "priority", "timeline", "past_decisions"
    )
    @classmethod
    def sanitize(cls, value: str, info) -> str:
        # Truncates to 2000 chars and raises if it matches known
        # prompt-injection patterns (Pydantic turns this into a 422).
        return sanitize_text(value, field_name=info.field_name)


# ── Routes ──────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the single-page frontend."""
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/decide", response_class=JSONResponse)
@limiter.limit(RATE_LIMIT)
async def decide(request: Request, req: DecisionRequest):
    """Run the orchestrator pipeline and return the merged report."""
    # Any exception here is caught by the global handler in security.py:
    # the client gets a generic message + error_id, the full traceback
    # is logged server-side.
    result = await run_orchestrator(
        decision=req.decision,
        risk_tolerance=req.risk_tolerance,
        priority=req.priority,
        timeline=req.timeline,
        past_decisions=req.past_decisions,
    )
    return JSONResponse(content=result)