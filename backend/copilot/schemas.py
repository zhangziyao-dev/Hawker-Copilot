from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import date
from backend.core.schemas import ConfidenceBreakdown


class CopilotRequest(BaseModel):
    item_name: str
    forecast_date: date
    location: Optional[str] = "Singapore"
    vendor_id: Optional[str] = None


class RevenueEstimate(BaseModel):
    prep_quantity: int
    price_per_unit: float
    potential_revenue: float
    expected_sellthrough_pct: float
    expected_revenue: float
    waste_quantity: int
    waste_cost: float
    vs_overprepare_savings: float


class RetrievedScenarioSummary(BaseModel):
    date: str
    day_name: str
    quantity_sold: int
    rain_flag: bool
    is_holiday: bool
    similarity_score: float


class LayerTrace(BaseModel):
    layer1_predicted: float
    layer1_confidence_lower: float
    layer1_confidence_upper: float
    layer1_top_features: Dict
    layer2_scenarios_found: int
    layer2_avg_similarity: float
    layer2_top_scenarios: List[RetrievedScenarioSummary]
    layer3_model: str
    layer3_prompt_tokens: Optional[int] = None


class OperationalRecommendation(BaseModel):
    item_name: str
    forecast_date: date
    vendor_id: Optional[str] = None
    stall_name: Optional[str] = None
    predicted_quantity: float
    recommended_prep_quantity: int
    confidence_level: str
    confidence_percentage: float
    confidence_breakdown: Optional[ConfidenceBreakdown] = None
    primary_factors: List[str]
    recommendation_text: str
    historical_context: str
    waste_risk: str
    shortage_risk: str
    revenue_estimate: Optional[RevenueEstimate] = None
    event_context: Optional[Dict] = None
    layer_trace: Optional[LayerTrace] = None   # ← NEW
    model_used: str