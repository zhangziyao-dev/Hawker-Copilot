from fastapi import APIRouter, HTTPException
from backend.copilot.schemas import CopilotRequest, OperationalRecommendation
from backend.copilot.advisor import run_full_pipeline
import logging

router = APIRouter(prefix="/copilot", tags=["copilot"])
logger = logging.getLogger(__name__)


@router.post("/recommend", response_model=OperationalRecommendation)
async def get_recommendation(request: CopilotRequest):
    """
    FULL PIPELINE endpoint — runs all 3 layers and returns
    a human-readable operational recommendation.
    This is the core demo endpoint.
    """
    try:
        result = run_full_pipeline(request)
        return result
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/alert/test")
async def send_test_alert(vendor_id: str = "vendor_001"):
    """
    Manually trigger a Telegram test alert.
    Use this for demo — shows real message on phone.
    """
    from backend.copilot.telegram_notifier import format_telegram_message, send_alert_sync
    from backend.core.vendor_profiles import get_vendor_by_id
    from datetime import date, timedelta

    vendor = get_vendor_by_id(vendor_id)
    stall_name = vendor.stall_name if vendor else "Demo Stall"

    test_message = format_telegram_message(
        stall_name=stall_name,
        item_name="Chicken Rice",
        forecast_date=date.today() + timedelta(days=1),
        recommended_qty=78,
        confidence_pct=82.0,
        confidence_level="HIGH",
        recommendation_text="Prepare 78 portions. Similar Fridays averaged 79. Clear weather supports normal lunch crowd.",
        waste_risk="LOW",
        shortage_risk="LOW",
        potential_revenue=351.0,
        expected_revenue=319.0,
        vs_overprepare_savings=45.0,
        primary_factors=[
            "Friday lunch crowd typically +15% vs weekday",
            "Clear weather supports normal foot traffic",
            "Historical Fridays averaged 74-92 portions"
        ],
        event_context={"is_monsoon_season": True},
    )

    sent = send_alert_sync(test_message)
    return {
        "status": "sent" if sent else "not_configured",
        "message_preview": test_message[:200] + "...",
        "tip": "Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env to enable"
    }

@router.get("/health")
async def health():
    return {"status": "ok", "layer": "ai-copilot"}
