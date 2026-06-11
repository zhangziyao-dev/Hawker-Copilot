from fastapi import APIRouter, HTTPException
from datetime import date, timedelta
from pydantic import BaseModel
from typing import List, Optional
import logging

from backend.core.data_ingestion import load_pos_data, fetch_weather_forecast
from backend.core.vendor_profiles import get_vendor_by_id
from backend.core.events import get_full_event_context
from backend.copilot.advisor import get_forecaster  # ← updated import

router = APIRouter(prefix="/forecast", tags=["forecast"])
logger = logging.getLogger(__name__)


class DayForecast(BaseModel):
    date: date
    day_name: str
    predicted_quantity: float
    confidence_lower: float
    confidence_upper: float
    is_holiday: bool
    is_school_holiday: bool
    holiday_name: Optional[str] = None
    event_name: Optional[str] = None
    rain_probability: float


class WeekForecastRequest(BaseModel):
    item_name: str
    vendor_id: Optional[str] = None
    start_date: Optional[date] = None


class WeekForecastResult(BaseModel):
    item_name: str
    vendor_id: Optional[str]
    stall_name: Optional[str]
    days: List[DayForecast]
    avg_predicted: float
    peak_day: str
    lowest_day: str


@router.post("/week", response_model=WeekForecastResult)
async def get_week_forecast(request: WeekForecastRequest):
    """
    7-day demand forecast — feeds the frontend chart.
    Returns predictions for next 7 days with event context.
    """
    try:
        vendor = get_vendor_by_id(request.vendor_id) if request.vendor_id else None
        area_type = vendor.area_type if vendor else "heartland"
        stall_name = vendor.stall_name if vendor else None

        # Vendor-specific training data and model
        forecaster = get_forecaster(request.item_name, request.vendor_id)
        historical_df = load_pos_data(
            item_name=request.item_name,
            vendor_id=request.vendor_id,
        )

        start = request.start_date or date.today()
        day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

        days = []
        for i in range(7):
            target = start + timedelta(days=i)
            weather = fetch_weather_forecast(target_date=target, city="Singapore")
            event_ctx = get_full_event_context(target, area_type)

            forecast = forecaster.predict(
                target_date=target,
                weather=weather,
                historical_df=historical_df,
                item_name=request.item_name,
                area_type=area_type,
            )

            days.append(DayForecast(
                date=target,
                day_name=day_names[target.weekday()],
                predicted_quantity=forecast.predicted_quantity,
                confidence_lower=forecast.confidence_lower,
                confidence_upper=forecast.confidence_upper,
                is_holiday=event_ctx["is_public_holiday"],
                is_school_holiday=event_ctx["is_school_holiday"],
                holiday_name=event_ctx.get("public_holiday_name"),
                event_name=event_ctx.get("nearby_event_name"),
                rain_probability=weather.rain_probability,
            ))

        quantities = [d.predicted_quantity for d in days]
        peak_idx = quantities.index(max(quantities))
        lowest_idx = quantities.index(min(quantities))
        peak_day = days[peak_idx].day_name
        lowest_day = days[lowest_idx].day_name

        return WeekForecastResult(
            item_name=request.item_name,
            vendor_id=request.vendor_id,
            stall_name=stall_name,
            days=days,
            avg_predicted=round(sum(quantities) / len(quantities), 1),
            peak_day=peak_day,
            lowest_day=lowest_day,
        )

    except Exception as e:
        logger.error(f"Week forecast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))