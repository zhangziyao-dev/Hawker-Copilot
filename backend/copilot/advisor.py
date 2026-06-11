import logging
from datetime import date

from backend.core.data_ingestion import load_pos_data, fetch_weather_forecast
from backend.core.forecaster import DemandForecaster, calculate_confidence
from backend.core.schemas import ForecastResult
from backend.core.vendor_profiles import get_vendor_by_id, VendorProfile
from backend.core.events import get_full_event_context
from backend.intelligence.schemas import RetrievalQuery, RetrievalResult
from backend.intelligence.retriever import retrieve_similar_scenarios
from backend.copilot.prompt_builder import build_copilot_prompt
from backend.copilot.llm_client import call_llm
from backend.copilot.schemas import (
    CopilotRequest, OperationalRecommendation, RevenueEstimate
)
from backend.database.db import save_recommendation, init_db
from backend.copilot.schemas import (
    CopilotRequest, OperationalRecommendation,
    RevenueEstimate, LayerTrace, RetrievedScenarioSummary
)
logger = logging.getLogger(__name__)

_forecaster: DemandForecaster = None

# Initialize DB on module load
init_db()


# Cache keyed by vendor+item
_forecasters: dict = {}

def get_forecaster(item_name: str, vendor_id: str = None) -> DemandForecaster:
    cache_key = f"{vendor_id}_{item_name}"
    if cache_key not in _forecasters or not _forecasters[cache_key].is_trained:
        df = load_pos_data(item_name=item_name, vendor_id=vendor_id)
        forecaster = DemandForecaster()
        forecaster.train(df)
        _forecasters[cache_key] = forecaster
        logger.info(f"Trained model for {cache_key}")
    return _forecasters[cache_key]


def calculate_revenue_estimate(
    prep_quantity: int,
    avg_price: float,
    predicted_qty: float,
) -> RevenueEstimate:
    """Calculate revenue and waste impact numbers."""
    overprepare_qty = int(predicted_qty * 1.25)  # gut-feel overprepare scenario
    expected_sell = min(prep_quantity, predicted_qty)
    sellthrough_pct = round((expected_sell / prep_quantity) * 100, 1) if prep_quantity > 0 else 0
    waste_qty = max(0, prep_quantity - int(expected_sell))
    waste_cost = round(waste_qty * avg_price, 2)
    potential_revenue = round(prep_quantity * avg_price, 2)
    expected_revenue = round(expected_sell * avg_price, 2)

    # Savings vs overpreparing
    overprepare_waste = max(0, overprepare_qty - int(predicted_qty))
    overprepare_waste_cost = round(overprepare_waste * avg_price, 2)
    savings = round(overprepare_waste_cost - waste_cost, 2)

    return RevenueEstimate(
        prep_quantity=prep_quantity,
        price_per_unit=avg_price,
        potential_revenue=potential_revenue,
        expected_sellthrough_pct=sellthrough_pct,
        expected_revenue=expected_revenue,
        waste_quantity=waste_qty,
        waste_cost=waste_cost,
        vs_overprepare_savings=max(0, savings),
    )


def run_full_pipeline(request: CopilotRequest) -> OperationalRecommendation:
    """
    Full 3-layer pipeline with vendor context, confidence scoring,
    revenue estimation, and DB persistence.
    """
    logger.info(f"Pipeline start: {request.item_name} | {request.forecast_date} | vendor: {request.vendor_id}")

    # ── Vendor Context ────────────────────────────────────────────
    vendor: VendorProfile = None
    area_type = "heartland"
    avg_price = 4.50
    stall_name = None

    if request.vendor_id:
        vendor = get_vendor_by_id(request.vendor_id)
        if vendor:
            area_type = vendor.area_type
            avg_price = vendor.avg_price_sgd
            stall_name = vendor.stall_name
            logger.info(f"Vendor loaded: {vendor.stall_name} ({area_type})")

    # ── LAYER 1: Forecast ─────────────────────────────────────────
    forecaster = get_forecaster(request.item_name, request.vendor_id)
    historical_df = load_pos_data(
    item_name=request.item_name,
    vendor_id=request.vendor_id,
    )
    weather = fetch_weather_forecast(
        target_date=request.forecast_date,
        city=request.location or "Singapore",
    )
    forecast: ForecastResult = forecaster.predict(
        target_date=request.forecast_date,
        weather=weather,
        historical_df=historical_df,
        item_name=request.item_name,
        area_type=area_type,
    )
    logger.info(f"Layer 1: predicted {forecast.predicted_quantity}")

    # ── LAYER 2: Retrieval ────────────────────────────────────────
    event_ctx = get_full_event_context(request.forecast_date, area_type)
    retrieval_query = RetrievalQuery(
        item_name=request.item_name,
        forecast_date=request.forecast_date,
        predicted_quantity=forecast.predicted_quantity,
        is_weekend=request.forecast_date.weekday() >= 5,
        is_holiday=event_ctx["is_public_holiday"],
        rain_flag=weather.rain_probability > 0.6,
        temperature=weather.temperature,
        humidity=weather.humidity,
    )
    retrieval: RetrievalResult = retrieve_similar_scenarios(retrieval_query, top_k=5)
    logger.info(f"Layer 2: {len(retrieval.top_scenarios)} scenarios retrieved")

    # ── Confidence Score ──────────────────────────────────────────
    avg_retrieval_score = float(
        sum(r.similarity_score for r in retrieval.top_scenarios) /
        len(retrieval.top_scenarios)
    ) if retrieval.top_scenarios else 0.5

    confidence = calculate_confidence(
        predicted_qty=forecast.predicted_quantity,
        recent_std=forecast.recent_std,
        retrieval_avg_score=avg_retrieval_score,
        is_holiday=event_ctx["is_public_holiday"],
        is_school_holiday=event_ctx["is_school_holiday"],
        is_eve_of_holiday=event_ctx["is_eve_of_holiday"],
        rain_probability=weather.rain_probability,
        has_historical_match=len(retrieval.top_scenarios) > 0,
    )
    logger.info(f"Confidence: {confidence.final_percentage}% ({confidence.final_level})")

    # ── LAYER 3: LLM ──────────────────────────────────────────────
    prompt = build_copilot_prompt(
        forecast=forecast,
        retrieval=retrieval,
        item_name=request.item_name,
        forecast_date=request.forecast_date,
        vendor=vendor,
        confidence=confidence,
        event_ctx=event_ctx,
    )
    llm_output = call_llm(prompt)
    logger.info("Layer 3: LLM recommendation generated")

    # ── Revenue Estimate ──────────────────────────────────────────
    prep_qty = llm_output["recommended_prep_quantity"]
    revenue = calculate_revenue_estimate(
        prep_quantity=prep_qty,
        avg_price=avg_price,
        predicted_qty=forecast.predicted_quantity,
    )

    
    # ── Layer Trace (for Demo Mode) ───────────────────────────────
    day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    top_scenarios_summary = [
        RetrievedScenarioSummary(
            date=str(r.scenario.date),
            day_name=day_names[r.scenario.day_of_week],
            quantity_sold=r.scenario.quantity_sold,
            rain_flag=r.scenario.rain_flag,
            is_holiday=r.scenario.is_holiday,
            similarity_score=r.similarity_score,
        )
        for r in retrieval.top_scenarios[:3]
    ]

    layer_trace = LayerTrace(
        layer1_predicted=forecast.predicted_quantity,
        layer1_confidence_lower=forecast.confidence_lower,
        layer1_confidence_upper=forecast.confidence_upper,
        layer1_top_features=forecast.key_features,
        layer2_scenarios_found=len(retrieval.top_scenarios),
        layer2_avg_similarity=round(avg_retrieval_score, 4),
        layer2_top_scenarios=top_scenarios_summary,
        layer3_model="gpt-4o-mini",
    )

    # ── Assemble Final Response ───────────────────────────────────
    result = OperationalRecommendation(
        item_name=request.item_name,
        forecast_date=request.forecast_date,
        vendor_id=request.vendor_id,
        stall_name=stall_name,
        predicted_quantity=forecast.predicted_quantity,
        recommended_prep_quantity=prep_qty,
        confidence_level=confidence.final_level,
        confidence_percentage=confidence.final_percentage,
        confidence_breakdown=confidence,
        primary_factors=llm_output["primary_factors"],
        recommendation_text=llm_output["recommendation_text"],
        historical_context=llm_output["historical_context"],
        waste_risk=llm_output["waste_risk"],
        shortage_risk=llm_output["shortage_risk"],
        revenue_estimate=revenue,
        event_context=event_ctx,
        layer_trace=layer_trace,
        model_used="gpt-4o-mini",
    )
 
    # ── Persist to DB ─────────────────────────────────────────────
    save_recommendation({
        "vendor_id": request.vendor_id,
        "item_name": request.item_name,
        "forecast_date": request.forecast_date,
        "predicted_quantity": forecast.predicted_quantity,
        "recommended_prep_quantity": prep_qty,
        "confidence_level": confidence.final_level,
        "confidence_percentage": confidence.final_percentage,
        "waste_risk": llm_output["waste_risk"],
        "shortage_risk": llm_output["shortage_risk"],
        "recommendation_text": llm_output["recommendation_text"],
        "historical_context": llm_output["historical_context"],
        "primary_factors": llm_output["primary_factors"],
        "model_used": "gpt-4o-mini",
    })

    # ── Telegram Alert ────────────────────────────────────────────
    try:
        from backend.copilot.telegram_notifier import (
            format_telegram_message, send_alert_sync
        )
        telegram_msg = format_telegram_message(
            stall_name=stall_name or "Your Stall",
            item_name=request.item_name,
            forecast_date=request.forecast_date,
            recommended_qty=prep_qty,
            confidence_pct=confidence.final_percentage,
            confidence_level=confidence.final_level,
            recommendation_text=llm_output["recommendation_text"],
            waste_risk=llm_output["waste_risk"],
            shortage_risk=llm_output["shortage_risk"],
            potential_revenue=revenue.potential_revenue,
            expected_revenue=revenue.expected_revenue,
            vs_overprepare_savings=revenue.vs_overprepare_savings,
            primary_factors=llm_output["primary_factors"],
            event_context=event_ctx,
        )
        # Send to vendor's chat ID if registered, else default
        vendor_chat_id = vendor.telegram_chat_id if vendor else None
        sent = send_alert_sync(telegram_msg, chat_id=vendor_chat_id)
        logger.info(f"Telegram alert: {'sent' if sent else 'skipped (not configured)'}")
    except Exception as e:
        logger.warning(f"Telegram alert failed silently: {e}")

    return result