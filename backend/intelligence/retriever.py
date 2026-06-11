import numpy as np
import logging
from datetime import date
from typing import List

from backend.intelligence.vector_store import DemandVectorStore
from backend.intelligence.embedder import build_scenario_narrative, embed_texts
from backend.intelligence.schemas import (
    DemandScenario, RetrievalQuery, RetrievalResult, RetrievedScenario
)
from backend.core.data_ingestion import generate_synthetic_pos_data
from backend.core.feature_engineering import build_features_from_history

logger = logging.getLogger(__name__)

_vector_store: DemandVectorStore = None


def build_scenarios_from_history(item_name: str = "Chicken Rice") -> List[DemandScenario]:
    """Convert historical POS data into DemandScenario objects for indexing."""
    df = generate_synthetic_pos_data(item_name=item_name, days=180)
    featured_df = build_features_from_history(df)

    scenarios = []
    for i, row in featured_df.iterrows():
        record = {
            "day_of_week": row["day_of_week"],
            "is_weekend": bool(row["is_weekend"]),
            "is_holiday": bool(row["is_holiday"]),
            "rain_flag": bool(row["rain_flag"]),
            "temperature": float(row["temperature"]),
            "humidity": float(row["humidity"]),
            "quantity_sold": int(row["quantity_sold"]),
            "rolling_mean_7": float(row["rolling_mean_7"]),
            "item_name": item_name,
        }
        narrative = build_scenario_narrative(record)

        scenario = DemandScenario(
            scenario_id=f"{item_name}-{i}",
            date=row["date"].date() if hasattr(row["date"], "date") else row["date"],
            item_name=item_name,
            quantity_sold=int(row["quantity_sold"]),
            day_of_week=int(row["day_of_week"]),
            is_weekend=bool(row["is_weekend"]),
            is_holiday=bool(row["is_holiday"]),
            rain_flag=bool(row["rain_flag"]),
            temperature=float(row["temperature"]),
            humidity=float(row["humidity"]),
            lag_1=float(row["lag_1"]),
            rolling_mean_7=float(row["rolling_mean_7"]),
            narrative=narrative,
        )
        scenarios.append(scenario)

    return scenarios


def get_vector_store(item_name: str = "Chicken Rice") -> DemandVectorStore:
    """Returns cached vector store, builds if not exists."""
    global _vector_store
    if _vector_store is None:
        logger.info("Initializing vector store...")
        scenarios = build_scenarios_from_history(item_name)
        _vector_store = DemandVectorStore()
        _vector_store.build(scenarios)
    return _vector_store


def retrieve_similar_scenarios(query: RetrievalQuery, top_k: int = 5) -> RetrievalResult:
    """
    Main retrieval function — Layer 2 output.
    Takes a forecast query, returns top-K similar historical scenarios.
    """
    # Build query narrative (same format as indexed scenarios)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    forecast_date = query.forecast_date
    dow = forecast_date.weekday()
    day_name = day_names[dow]

    weather = "rainy" if query.rain_flag else "clear"
    weekend = "weekend" if query.is_weekend else "weekday"
    holiday = " and public holiday" if query.is_holiday else ""

    query_narrative = (
        f"{day_name} {weekend}{holiday} with {weather} weather. "
        f"Temperature {query.temperature:.0f}C. "
        f"Forecasted {query.predicted_quantity:.0f} portions of {query.item_name}. "
        f"Looking for similar historical demand patterns."
    )

    # Search vector store
    store = get_vector_store(query.item_name)
    raw_results = store.search(query_narrative, top_k=top_k)

    # Build ranked results
    ranked = []
    for rank, (scenario, score) in enumerate(raw_results, start=1):
        ranked.append(RetrievedScenario(
            scenario=scenario,
            similarity_score=round(score, 4),
            rank=rank,
        ))

    # Aggregate stats
    quantities = [r.scenario.quantity_sold for r in ranked]

    return RetrievalResult(
        query_narrative=query_narrative,
        top_scenarios=ranked,
        avg_historical_quantity=round(float(np.mean(quantities)), 1),
        min_historical_quantity=float(min(quantities)),
        max_historical_quantity=float(max(quantities)),
        retrieval_model="all-MiniLM-L6-v2",
    )