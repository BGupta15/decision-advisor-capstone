"""
Risk Assessment Agent
Evaluates risk factors for a decision and returns structured JSON:
{score_1_to_10, best_case, worst_case, recommendation}
"""

import json
from agents.groq_client import client, MODEL

SYSTEM_INSTRUCTION = """You are a risk assessment specialist. Evaluate the risk profile of the
user's decision based on their stated risk tolerance, priority, and timeline.

You MUST respond with ONLY valid JSON — no markdown, no code fences, no extra text.
Use this exact schema:
{
  "score_1_to_10": <integer 1-10 where 10 is highest risk>,
  "best_case": "Description of the best realistic outcome",
  "worst_case": "Description of the worst realistic outcome",
  "recommendation": "Your specific, actionable recommendation"
}

Be honest and specific. Reference the user's risk tolerance in your recommendation."""


async def run_risk_agent(
    decision: str, risk_tolerance: str, priority: str, timeline: str
) -> dict:
    """Assess risk for the given decision context."""
    prompt = (
        f"Evaluate the risk of this decision: '{decision}'.\n"
        f"Risk tolerance: {risk_tolerance}\n"
        f"Top priority: {priority}\n"
        f"Timeline: {timeline}\n\n"
        "Provide a thorough risk assessment as JSON only."
    )

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

    try:
        text = response.choices[0].message.content
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        return json.loads(text)
    except Exception:
        return {
            "score_1_to_10": 5,
            "best_case": "Unable to parse risk data",
            "worst_case": "Analysis encountered an error",
            "recommendation": text if text else "No response from model",
        }
