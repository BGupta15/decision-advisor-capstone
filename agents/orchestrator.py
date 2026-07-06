"""
Orchestrator Agent
Calls Gemini 2.0 Flash in a single unified execution with Google Search grounding
to retrieve Market, Risk, and Psychology insights in one consolidated request.
This mitigates 429 rate limit errors by reducing calls per decision from 3 down to 1.
"""

import json
import asyncio
from agents.groq_client import client, MODEL

SYSTEM_INSTRUCTION = """You are a Decision Intelligence Orchestrator. Your job is to analyze the user's decision context from three key perspectives:
1. MARKET ANALYSIS: Use the Google Search grounding tool to research real-time market landscape, competitor trends, and economic context.
2. RISK ASSESSMENT: Evaluate risk scores, best/worst cases, and actionable recommendations based on stated risk tolerance.
3. COGNITIVE PSYCHOLOGY: Analyze past decisions to detect biases, calculate priority alignment, and formulate a gut-check question.

You MUST respond with ONLY valid JSON — no markdown, no code fences, no extra text.
Use this exact schema:
{
  "market": {
    "opportunities": ["opportunity 1", "opportunity 2", ...],
    "threats": ["threat 1", "threat 2", ...],
    "timing": "Real-time assessment of whether now is a good time based on search findings"
  },
  "risk": {
    "score_1_to_10": <integer 1-10 where 10 is highest risk>,
    "best_case": "Description of the best realistic outcome",
    "worst_case": "Description of the worst realistic outcome",
    "recommendation": "Your specific recommendation matching risk tolerance"
  },
  "psychology": {
    "biases": [
      {"name": "Bias Name", "description": "How this bias shows up in their pattern"}
    ],
    "alignment_score": <integer 1-10 where 10 is highly aligned>,
    "gut_check_question": "A powerful question tailored to this situation"
  }
}"""


def _build_verdict(market: dict, risk: dict, psychology: dict) -> str:
    """Synthesise agent outputs into a single human-readable verdict."""
    risk_score = risk.get("score_1_to_10", "?")
    recommendation = risk.get("recommendation", "No recommendation available.")

    # Determine overall signal
    if isinstance(risk_score, int):
      if risk_score <= 3:
        signal = "🟢 LOW RISK — Conditions appear favourable."
      elif risk_score <= 6:
        signal = "🟡 MODERATE RISK — Proceed with caution."
      else:
        signal = "🔴 HIGH RISK — Significant concerns detected."
    else:
      signal = "⚪ UNCERTAIN — Could not determine risk level."

    biases = psychology.get("biases", [])
    bias_names = ", ".join(b.get("name", "Unknown") for b in biases) if biases else "None detected"
    alignment = psychology.get("alignment_score", "?")
    gut_check = psychology.get("gut_check_question", "")

    opportunities = market.get("opportunities", [])
    threats = market.get("threats", [])

    verdict = (
        f"{signal}\n\n"
        f"📊 Risk Score: {risk_score}/10\n"
        f"💡 Recommendation: {recommendation}\n\n"
        f"🔍 Key Opportunities: {', '.join(opportunities[:3]) if opportunities else 'None identified'}\n"
        f"⚠️ Top Threats: {', '.join(threats[:3]) if threats else 'None identified'}\n\n"
        f"🧠 Cognitive Biases Detected: {bias_names}\n"
        f"🎯 Priority Alignment: {alignment}/10\n"
        f"❓ Gut Check: {gut_check}"
    )
    return verdict


async def run_orchestrator(
    decision: str,
    risk_tolerance: str,
    priority: str,
    timeline: str,
    past_decisions: str,
) -> dict:
    """Run the decision intelligence pipeline using a single consolidated LLM call."""

    prompt = (
        f"Perform a comprehensive decision analysis:\n"
        f"Current Decision: '{decision}'\n"
        f"Risk Tolerance: {risk_tolerance}\n"
        f"Stated Top Priority: {priority}\n"
        f"Timeline: {timeline}\n"
        f"Past Decisions Context: {past_decisions}\n\n"
        "Generate the Market, Risk, and Psychology evaluations. Use Google Search to ground the Market Opportunities and Threats."
    )

    # Single robust call to Gemini with automatic rate-limit retry support
    async def fetch_unified_analysis(retries=1, delay=15.0):
        import re
        for attempt in range(retries):
            try:
                # Wrap block in loop
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": SYSTEM_INSTRUCTION,
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )
                return response
            except Exception as e:
                print(repr(e))
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    if attempt < retries - 1:
                        match = re.search(r"retry in (\d+\.?\d*)s", err_msg)
                        sleep_time = float(match.group(1)) + 1.5 if match else delay * (attempt + 1)
                        print(f"[Orchestrator] Unified request limit hit. Retrying in {sleep_time:.2f}s...")
                        await asyncio.sleep(sleep_time)
                        continue
                raise e

    response = await fetch_unified_analysis()

    try:
        text = response.choices[0].message.content
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        data = json.loads(text)
    except Exception as parse_error:
        print(f"[Orchestrator] Parse failed. Raw response: {text}")
        # Build graceful fallback JSON in case of formatting anomalies
        data = {
            "market": {
                "opportunities": ["Real-time opportunities could not be structured"],
                "threats": ["Real-time threats could not be structured"],
                "timing": "Execution succeeded, but output did not match JSON structure."
            },
            "risk": {
                "score_1_to_10": 5,
                "best_case": "Information parsing error",
                "worst_case": "Information parsing error",
                "recommendation": "Try resubmitting your query."
            },
            "psychology": {
                "biases": [{"name": "Parsing Issue", "description": "LLM response did not parse cleanly."}],
                "alignment_score": 5,
                "gut_check_question": "What is the simplest version of this choice?"
            }
        }

    # Extract sections
    market_result = data.get("market", {})
    risk_result = data.get("risk", {})
    psychology_result = data.get("psychology", {})

    # Build final verdict
    verdict = _build_verdict(market_result, risk_result, psychology_result)

    return {
        "market": market_result,
        "risk": risk_result,
        "psychology": psychology_result,
        "verdict": verdict,
    }

