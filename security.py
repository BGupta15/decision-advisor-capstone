"""
security.py — Security utilities for the Decision Advisor backend.

Provides:
  * Rate limiting (5 requests/minute per IP) via slowapi
  * Regex-based prompt-injection detection + input truncation
  * Secure error handling: generic client-facing messages, full
    tracebacks logged server-side with a correlation ID
"""

import logging
import re
import traceback
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ── Logging ──────────────────────────────────────────────────────────────────
# Full details (including tracebacks) go here — never sent to the client.
logger = logging.getLogger("decision_advisor")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(handler)


# ── Rate limiting ────────────────────────────────────────────────────────────
# 5 requests per minute per client IP. get_remote_address respects
# X-Forwarded-For if you later run behind a proxy/load balancer.
limiter = Limiter(key_func=get_remote_address, default_limits=[])

RATE_LIMIT = "5/minute"


def setup_rate_limiting(app: FastAPI) -> None:
    """Attach the limiter + a clean 429 handler to the app."""
    app.state.limiter = limiter

    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        logger.warning(
            "Rate limit exceeded for %s on %s",
            get_remote_address(request),
            request.url.path,
        )
        return JSONResponse(
            status_code=429,
            content={"error": "Too many requests. Please slow down and try again shortly."},
        )

    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)


# ── Input sanitization ───────────────────────────────────────────────────────
MAX_FIELD_LENGTH = 2000

# Common prompt-injection / jailbreak phrasings. Case-insensitive.
# This is defense-in-depth, not a guarantee — pair with least-privilege
# agent design and never let sanitized text be treated as trusted instructions.
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|the)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"forget\s+(all\s+)?(previous|prior|above|your)\s+instructions?",
    r"you\s+are\s+now\s+(a|an|in)\s+\w+\s*(mode)?",
    r"system\s*prompt",
    r"\bnew\s+instructions?\s*:",
    r"act\s+as\s+(if\s+you\s+are\s+)?(a|an)\s+\w+",
    r"reveal\s+(your|the)\s+(system\s+)?prompt",
    r"do\s+anything\s+now",
    r"\bDAN\b",
    r"override\s+(your|the|all)\s+(rules|guidelines|instructions)",
    r"<\s*/?system\s*>",
    r"\[\s*/?system\s*\]",
    r"jailbreak",
    r"pretend\s+(you\s+are|to\s+be)\s+",
    r"respond\s+as\s+(if\s+)?(you\s+(are|were)|an?)\s+",
    r"this\s+is\s+a\s+test\s+of\s+your\s+(guidelines|rules|instructions)",
]

_INJECTION_REGEX = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


class PromptInjectionError(ValueError):
    """Raised when a field appears to contain a prompt-injection attempt."""


def sanitize_text(value: str, field_name: str = "field") -> str:
    """
    Truncate to MAX_FIELD_LENGTH and reject text that matches known
    prompt-injection patterns. Raises PromptInjectionError on a match.
    """
    if not isinstance(value, str):
        return value

    truncated = value[:MAX_FIELD_LENGTH]

    match = _INJECTION_REGEX.search(truncated)
    if match:
        logger.warning(
            "Potential prompt injection detected in field '%s': matched pattern near %r",
            field_name,
            truncated[max(0, match.start() - 20): match.end() + 20],
        )
        raise PromptInjectionError(
            f"Input for '{field_name}' contains disallowed content."
        )

    return truncated


# ── Secure error handling ───────────────────────────────────────────────────
def setup_error_handling(app: FastAPI) -> None:
    """
    Catch-all handler: logs full tracebacks server-side with a correlation
    ID, returns only a generic message + that ID to the client.
    """

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        error_id = uuid.uuid4().hex[:12]
        logger.error(
            "Unhandled exception [%s] on %s %s:\n%s",
            error_id,
            request.method,
            request.url.path,
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "An unexpected error occurred. Please try again later.",
                "error_id": error_id,
            },
        )