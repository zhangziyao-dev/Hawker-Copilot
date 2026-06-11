import json
import logging
import os
from openai import OpenAI
from backend.config import config

logger = logging.getLogger(__name__)

_client = None


def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def call_llm(prompt: str) -> dict:
    """
    Calls OpenAI and returns parsed JSON response.
    Falls back to rule-based response if no API key.
    """
    if not config.OPENAI_API_KEY:
        logger.warning("No OpenAI key — using rule-based fallback.")
        return _rule_based_fallback(prompt)

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",       # fast + cheap, perfect for hackathon
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise operational AI assistant. Always respond with valid JSON only. No markdown, no explanation outside JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,           # low temp = consistent, factual responses
            max_tokens=600,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        return json.loads(raw)

    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON: {e}")
        return _rule_based_fallback(prompt)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return _rule_based_fallback(prompt)


def _rule_based_fallback(prompt: str) -> dict:
    import re
    qty_match  = re.search(r"Predicted demand: ([\d.]+)", prompt)
    hist_match = re.search(r"Historical average on similar days: ([\d.]+)", prompt)
    low_match  = re.search(r"Confidence range: ([\d.]+)", prompt)
    high_match = re.search(r"to ([\d.]+) portions\n- Model", prompt)

    predicted  = float(qty_match.group(1))  if qty_match  else 80.0
    historical = float(hist_match.group(1)) if hist_match else 75.0
    conf_low   = float(low_match.group(1))  if low_match  else predicted * 0.85
    conf_high  = float(high_match.group(1)) if high_match else predicted * 1.15

    # Blended: 60% forecast + 40% historical + 8% buffer
    blended  = (predicted * 0.6) + (historical * 0.4)
    prep_qty = int(round(blended * 1.08))

    spread     = conf_high - conf_low
    confidence = "HIGH" if spread < 20 else "MEDIUM" if spread < 35 else "LOW"
    waste_risk    = "LOW"    if prep_qty <= predicted * 1.15 else "MEDIUM"
    shortage_risk = "LOW"    if prep_qty >= predicted * 0.95 else "MEDIUM"

    return {
        "recommended_prep_quantity": prep_qty,
        "confidence_level": confidence,
        "primary_factors": [
            f"ML forecast predicts {predicted:.0f} portions",
            f"Similar historical days averaged {historical:.0f} portions",
            "8% safety buffer applied to avoid shortage"
        ],
        "recommendation_text": (
            f"Prepare {prep_qty} portions based on a blend of today's "
            f"forecast ({predicted:.0f}) and historical similar days "
            f"({historical:.0f}). Confidence range is {conf_low:.0f} to "
            f"{conf_high:.0f} portions. Start prep early and monitor "
            f"sell rate by midday."
        ),
        "historical_context": (
            f"On similar past days, sales ranged with an average of "
            f"{historical:.0f} portions."
        ),
        "waste_risk": waste_risk,
        "shortage_risk": shortage_risk,
    }