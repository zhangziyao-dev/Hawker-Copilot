from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class DemandScenario(BaseModel):
    """A single historical demand scenario stored in vector DB."""
    scenario_id: str
    date: date
    item_name: str
    quantity_sold: int
    day_of_week: int
    is_weekend: bool
    is_holiday: bool
    rain_flag: bool
    temperature: float
    humidity: float
    lag_1: float
    rolling_mean_7: float
    narrative: str  # human-readable description used for embedding


class RetrievalQuery(BaseModel):
    item_name: str
    forecast_date: date
    predicted_quantity: float
    is_weekend: bool
    is_holiday: bool
    rain_flag: bool
    temperature: float
    humidity: float


class RetrievedScenario(BaseModel):
    scenario: DemandScenario
    similarity_score: float
    rank: int


class RetrievalResult(BaseModel):
    query_narrative: str
    top_scenarios: List[RetrievedScenario]
    avg_historical_quantity: float
    min_historical_quantity: float
    max_historical_quantity: float
    retrieval_model: str