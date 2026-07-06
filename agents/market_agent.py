"""
Market Analysis Agent
Uses Google Search grounding to find real-time market data,
then returns JSON: {opportunities, threats, timing}
"""

import json
from agents.groq_client import client, MODEL

SYSTEM_INSTRUCTION = """You are a market analysis expert. Given a decision the user is considering,
analyze the market using your knowledge of industry trends, economics, business strategy, and technology.

You MUST respond with ONLY valid JSON — no markdown, no code fences, no extra text.
Use this exact schema:
{
  "opportunities": ["opportunity 1", "opportunity 2", ...],
  "threats": ["threat 1", "threat 2", ...],
  "timing": "Your assessment of whether NOW is a good time and why"
}

Keep each array to 3-5 items. Be specific and data-driven."""


async def run_market_agent(decision: str, timeline: str) -> dict:
    """Analyse market conditions relevant to the user's decision."""
    prompt = (
        f"Analyse the market landscape for this decision: '{decision}'. "
        f"Timeline: {timeline}. "
        "Based on your knowledge of industry trends, economics, business strategy, "
        "and market conditions, identify opportunities, threats, and whether now is "
        "a good time to make this decision. "
        "Return ONLY valid JSON."
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
        # Strip markdown code fences if the model wraps them
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        return json.loads(text)
    except Exception:
        return {
            "opportunities": ["Unable to parse market data"],
            "threats": ["Analysis encountered an error"],
            "timing": text if text else "No response from model",
        }
