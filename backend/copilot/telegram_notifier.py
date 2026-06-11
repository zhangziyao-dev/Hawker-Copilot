import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


def format_telegram_message(
    stall_name: str,
    item_name: str,
    forecast_date: date,
    recommended_qty: int,
    confidence_pct: float,
    confidence_level: str,
    recommendation_text: str,
    waste_risk: str,
    shortage_risk: str,
    potential_revenue: float,
    expected_revenue: float,
    vs_overprepare_savings: float,
    primary_factors: list,
    event_context: dict = None,
) -> str:
    """
    Formats the Telegram alert message.
    Designed to feel like a WhatsApp message, not a corporate report.
    """
    # Risk emojis
    risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
    confidence_emoji = {"HIGH": "💪", "MEDIUM": "👍", "LOW": "⚠️"}

    # Event flags
    event_flags = []
    if event_context:
        if event_context.get("is_public_holiday"):
            event_flags.append(f"🎉 {event_context.get('public_holiday_name', 'Public Holiday')}")
        if event_context.get("is_school_holiday"):
            event_flags.append("🏫 School Holidays")
        if event_context.get("is_payday_period"):
            event_flags.append("💰 Payday Period")
        if event_context.get("is_monsoon_season"):
            event_flags.append("🌧️ Monsoon Season")
        if event_context.get("nearby_event_name"):
            event_flags.append(f"🎪 {event_context['nearby_event_name']}")

    event_section = ""
    if event_flags:
        event_section = "\n📅 *Active Signals:*\n" + "\n".join(f"  {f}" for f in event_flags)

    factors_text = "\n".join(f"  • {f}" for f in primary_factors[:3])

    message = f"""🍜 *HAWKER COPILOT — Prep Alert*
━━━━━━━━━━━━━━━━━━━━━━━
🏪 *{stall_name}*
📆 Tomorrow: {forecast_date.strftime('%A, %d %b %Y')}
{event_section}

📊 *AI Recommendation*
Prepare *{recommended_qty} portions* of {item_name}

{confidence_emoji.get(confidence_level, '👍')} Confidence: *{confidence_pct:.0f}%* ({confidence_level})

💡 *Why this number?*
{factors_text}

📝 {recommendation_text}

💰 *Revenue Estimate*
  • Expected: *${expected_revenue:.0f}*
  • If you overprepare: ~${expected_revenue - vs_overprepare_savings:.0f} after waste
  • AI saves you: *~${vs_overprepare_savings:.0f}* today

⚠️ *Risk Assessment*
  {risk_emoji.get(waste_risk, '🟡')} Waste Risk: {waste_risk}
  {risk_emoji.get(shortage_risk, '🟡')} Shortage Risk: {shortage_risk}
━━━━━━━━━━━━━━━━━━━━━━━
_Powered by Hawker Copilot AI_ 🤖"""

    return message


async def send_telegram_alert(
    message: str,
    chat_id: Optional[str] = None,
) -> bool:
    """
    Sends formatted message via Telegram Bot API.
    Returns True if successful, False if failed/no token.
    """
    from backend.config import config

    token = config.TELEGRAM_BOT_TOKEN
    target_chat_id = chat_id or config.TELEGRAM_CHAT_ID

    if not token or not target_chat_id:
        logger.warning("Telegram not configured — skipping alert.")
        return False

    try:
        import telegram
        bot = telegram.Bot(token=token)
        await bot.send_message(
            chat_id=target_chat_id,
            text=message,
            parse_mode="Markdown",
        )
        logger.info(f"Telegram alert sent to {target_chat_id}")
        return True
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


def send_alert_sync(message: str, chat_id: Optional[str] = None) -> bool:
    """
    Synchronous wrapper for FastAPI endpoints.
    FastAPI uses async but advisor.py calls this synchronously.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    send_telegram_alert(message, chat_id)
                )
                return future.result(timeout=10)
        else:
            return loop.run_until_complete(send_telegram_alert(message, chat_id))
    except Exception as e:
        logger.error(f"Telegram sync wrapper failed: {e}")
        return False