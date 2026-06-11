from datetime import date
from backend.core.schemas import ForecastResult, ConfidenceBreakdown
from backend.intelligence.schemas import RetrievalResult
from typing import Optional


def build_copilot_prompt(
    forecast: ForecastResult,
    retrieval: RetrievalResult,
    item_name: str,
    forecast_date: date,
    vendor=None,
    confidence=None,
    event_ctx: dict = None,
) -> str:

    scenarios_text = ""
    for r in retrieval.top_scenarios[:3]:
        s = r.scenario
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        day = day_names[s.day_of_week]
        weather = "rainy" if s.rain_flag else "clear"
        holiday = " (holiday)" if s.is_holiday else ""
        scenarios_text += (
            f"  - {s.date} ({day}{holiday}, {weather}): "
            f"sold {s.quantity_sold} portions\n"
        )

    feature_lines = "\n".join(
        [f"  - {k}: importance {v:.3f}" for k, v in forecast.key_features.items()]
    )

    vendor_context = ""
    if vendor:
        vendor_context = f"""
## VENDOR CONTEXT
- Stall: {vendor.stall_name}
- Location: {vendor.hawker_centre} ({vendor.area_type} area)
- Near MRT: {"Yes - " + vendor.mrt_station if vendor.near_mrt else "No"}
- Near School: {"Yes - " + (vendor.school_name or "") if vendor.near_school else "No"}
- Avg price: SGD ${vendor.avg_price_sgd:.2f}
- Daily capacity: {vendor.daily_capacity} portions
"""

    event_context = ""
    if event_ctx:
        active = []
        if event_ctx.get("is_public_holiday"):
            active.append(f"PUBLIC HOLIDAY: {event_ctx.get('public_holiday_name')}")
        if event_ctx.get("is_eve_of_holiday"):
            active.append("Eve of public holiday")
        if event_ctx.get("is_school_holiday"):
            active.append(f"SCHOOL HOLIDAY: {event_ctx.get('school_holiday_name')}")
        if event_ctx.get("is_payday_period"):
            active.append("Payday period (end of month)")
        if event_ctx.get("is_monsoon_season"):
            active.append("Monsoon season")
        if event_ctx.get("nearby_event_name"):
            active.append(f"Nearby event: {event_ctx['nearby_event_name']}")
        event_context = "## ACTIVE CONTEXT FLAGS\n" + "\n".join(f"  - {a}" for a in active) if active else ""

    confidence_text = ""
    if confidence:
        confidence_text = f"""
## CONFIDENCE SCORE: {confidence.final_percentage}% ({confidence.final_level})
- Retrieval quality: {confidence.retrieval_quality:.1f}/30
- Sales stability: {confidence.sales_stability:.1f}/30
- Weather certainty: {confidence.weather_certainty:.1f}/20
- Penalties applied: -{confidence.penalties:.1f}
"""

    prompt = f"""You are an AI operational copilot for a Singapore hawker food stall.
Give precise, practical prep advice based on demand forecast data.
Use simple language suitable for a hawker owner.
{vendor_context}
## TODAY'S FORECAST
- Item: {item_name}
- Date: {forecast_date} ({forecast_date.strftime('%A')})
- Predicted demand: {forecast.predicted_quantity} portions
- Confidence range: {forecast.confidence_lower} to {forecast.confidence_upper} portions
{event_context}
{confidence_text}
## KEY DEMAND DRIVERS
{feature_lines}

## SIMILAR HISTORICAL DAYS (top 3)
{scenarios_text}
- Historical average: {retrieval.avg_historical_quantity} portions
- Historical range: {retrieval.min_historical_quantity} to {retrieval.max_historical_quantity} portions

## YOUR TASK
Respond in this EXACT JSON format:
{{
  "recommended_prep_quantity": <integer>,
  "confidence_level": "<HIGH|MEDIUM|LOW>",
  "primary_factors": ["<factor1>", "<factor2>", "<factor3>"],
  "recommendation_text": "<2-3 sentences, simple language, specific numbers>",
  "historical_context": "<1 sentence on what similar past days showed>",
  "waste_risk": "<LOW|MEDIUM|HIGH>",
  "shortage_risk": "<LOW|MEDIUM|HIGH>"
}}

Be specific. Use actual numbers. Write like you are advising an experienced hawker uncle."""

    return prompt