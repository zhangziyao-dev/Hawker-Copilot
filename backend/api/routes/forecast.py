from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import date
import logging

from backend.core.schemas import ForecastRequest, ForecastResult
from backend.core.data_ingestion import load_pos_data, fetch_weather_forecast
from backend.core.forecaster import DemandForecaster

router = APIRouter(prefix="/forecast", tags=["forecast"])
logger = logging.getLogger(__name__)

# Module-level model cache (loaded once on first request)
_forecaster: DemandForecaster = None


def get_forecaster(item_name: str = "Chicken Rice") -> DemandForecaster:
    global _forecaster
    if _forecaster is None or not _forecaster.is_trained:
        logger.info("Training forecaster on startup...")
        df = load_pos_data(item_name=item_name)
        _forecaster = DemandForecaster()
        stats = _forecaster.train(df)
        logger.info(f"Forecaster ready. Stats: {stats}")
    return _forecaster


@router.post("/predict", response_model=ForecastResult)
async def predict_demand(request: ForecastRequest):
    """
    Predict demand for a hawker item on a given date.
    Layer 1 output — feeds into Layer 2 (retrieval) and Layer 3 (LLM).
    """
    try:
        forecaster = get_forecaster(item_name=request.item_name)
        historical_df = load_pos_data(item_name=request.item_name)
        weather = fetch_weather_forecast(
            target_date=request.forecast_date,
            city=request.location or "Singapore",
        )
        result = forecaster.predict(
            target_date=request.forecast_date,
            weather=weather,
            historical_df=historical_df,
            item_name=request.item_name,
        )
        return result
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/train-stats")
async def get_training_stats():
    """Returns model training performance metrics."""
    forecaster = get_forecaster()
    return {
        "status": "trained",
        "stats": forecaster.training_stats,
        "feature_importance": forecaster.feature_importance,
    }


@router.get("/health")
async def health():
    return {"status": "ok", "layer": "core-forecast-engine"}