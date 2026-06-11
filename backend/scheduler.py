import logging
import pytz
from datetime import date, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler = None
SGT = pytz.timezone("Asia/Singapore")


async def _send_nightly_alerts():
    """
    Core job — runs at 7PM SGT every day.
    Loops all vendors, generates forecast for tomorrow,
    sends personalized Telegram alert per item per vendor.
    """
    from backend.core.vendor_profiles import get_all_vendors
    from backend.copilot.advisor import run_full_pipeline
    from backend.copilot.schemas import CopilotRequest

    tomorrow = date.today() + timedelta(days=1)
    vendors = get_all_vendors()

    logger.info(f"Nightly alert job started. {len(vendors)} vendors, target date: {tomorrow}")

    success_count = 0
    skip_count = 0
    fail_count = 0

    for vendor in vendors:
        # Only send to vendors with Telegram configured
        if not vendor.telegram_chat_id:
            logger.info(f"Skipping {vendor.stall_name} — no Telegram chat ID")
            skip_count += 1
            continue

        for item in vendor.items:
            try:
                logger.info(f"Generating alert: {vendor.stall_name} | {item}")
                request = CopilotRequest(
                    item_name=item,
                    forecast_date=tomorrow,
                    location="Singapore",
                    vendor_id=vendor.vendor_id,
                )
                # run_full_pipeline already sends Telegram internally
                result = run_full_pipeline(request)
                logger.info(
                    f"Alert sent: {vendor.stall_name} | {item} | "
                    f"prep={result.recommended_prep_quantity} | "
                    f"confidence={result.confidence_percentage}%"
                )
                success_count += 1

            except Exception as e:
                logger.error(f"Alert failed: {vendor.stall_name} | {item} | {e}")
                fail_count += 1

    logger.info(
        f"Nightly job complete. "
        f"Sent: {success_count} | Skipped: {skip_count} | Failed: {fail_count}"
    )
    return {
        "sent": success_count,
        "skipped": skip_count,
        "failed": fail_count,
        "target_date": str(tomorrow),
    }


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=SGT)

        # Nightly alert — 7:00 PM SGT every day
        _scheduler.add_job(
            _send_nightly_alerts,
            trigger="cron",
            hour=19,
            minute=0,
            id="nightly_alerts",
            name="Nightly Vendor Prep Alerts",
            replace_existing=True,
        )

        logger.info("Scheduler initialized. Nightly alerts at 19:00 SGT.")
    return _scheduler


def start_scheduler():
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped.")