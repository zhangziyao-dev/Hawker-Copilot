from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import date


class SalesRecord(BaseModel):
    date: date
    item_name: str
    quantity_sold: int
    revenue: float


class ForecastRequest(BaseModel):
    item_name: str
    forecast_date: date
    location: Optional[str] = "Singapore"
    include_weather: Optional[bool] = True
    vendor_id: Optional[str] = None


class ConfidenceBreakdown(BaseModel):
    retrieval_quality: float
    sales_stability: float
    weather_certainty: float
    day_predictability: float
    lag_signal: float
    penalties: float
    final_percentage: float
    final_level: str


class ForecastResult(BaseModel):
    item_name: str
    forecast_date: date
    predicted_quantity: float
    confidence_lower: float
    confidence_upper: float
    key_features: Dict
    model_used: str
    recent_std: float = 0.0
    event_context: Optional[Dict] = None


class WeatherData(BaseModel):
    date: date
    temperature: float
    humidity: float
    weather_condition: str
    rain_probability: float