from fastapi import APIRouter, HTTPException
from datetime import date, timedelta
import logging

router = APIRouter(prefix="/scheduler", tags=["scheduler"])
logger = logging.getLogger(__name__)


@router.post("/trigger/nightly")
async def trigger_nightly_alerts():
    """
    Manually trigger the nightly alert job.
    Use this for demo — simulates the 7PM scheduler firing.
    """
    try:
        from backend.scheduler import _send_nightly_alerts
        result = await _send_nightly_alerts()
        return {
            "status": "completed",
            "result": result,
            "message": f"Nightly alerts triggered manually for {result['target_date']}"
        }
    except Exception as e:
        logger.error(f"Manual trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/vendor/{vendor_id}")
async def trigger_vendor_alert(vendor_id: str, forecast_date: str = None):
    """
    Trigger alert for a single vendor — useful for testing
    individual vendor messages during demo.
    """
    from backend.core.vendor_profiles import get_vendor_by_id
    from backend.copilot.advisor import run_full_pipeline
    from backend.copilot.schemas import CopilotRequest

    vendor = get_vendor_by_id(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")

    target = date.today() + timedelta(days=1)
    if forecast_date:
        try:
            target = date.fromisoformat(forecast_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    results = []
    for item in vendor.items:
        try:
            result = run_full_pipeline(CopilotRequest(
                item_name=item,
                forecast_date=target,
                location="Singapore",
                vendor_id=vendor_id,
            ))
            results.append({
                "item": item,
                "prep_quantity": result.recommended_prep_quantity,
                "confidence": f"{result.confidence_percentage}%",
                "revenue_estimate": result.revenue_estimate.expected_revenue
                    if result.revenue_estimate else None,
                "telegram_sent": vendor.telegram_chat_id is not None,
            })
        except Exception as e:
            results.append({"item": item, "error": str(e)})

    return {
        "vendor": vendor.stall_name,
        "forecast_date": str(target),
        "items_processed": len(results),
        "results": results,
    }


@router.get("/status")
async def get_scheduler_status():
    """Returns current scheduler status and next run time."""
    from backend.scheduler import get_scheduler
    scheduler = get_scheduler()
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else "not scheduled",
        })
    return {
        "running": scheduler.running,
        "timezone": "Asia/Singapore",
        "jobs": jobs,
    }