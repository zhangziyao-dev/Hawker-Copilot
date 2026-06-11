from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List
import logging

logger = logging.getLogger(__name__)

# Loads once, cached in memory
_model = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")  # 80MB, fast, good quality
        logger.info("Embedding model loaded.")
    return _model


def embed_texts(texts: List[str]) -> np.ndarray:
    """Convert list of strings to embedding matrix. Shape: (N, 384)"""
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return embeddings.astype(np.float32)


def embed_single(text: str) -> np.ndarray:
    """Embed a single string. Returns shape (1, 384)"""
    return embed_texts([text])


def build_scenario_narrative(record: dict) -> str:
    """
    Converts a raw data record into a human-readable narrative for embedding.
    This is the KEY design decision — richer narratives = better retrieval.
    """
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_name = day_names[int(record.get("day_of_week", 0))]

    weather = "rainy" if record.get("rain_flag", 0) else "clear"
    weekend = "weekend" if record.get("is_weekend", 0) else "weekday"
    holiday = " and public holiday" if record.get("is_holiday", 0) else ""
    qty = int(record.get("quantity_sold", 0))
    temp = record.get("temperature", 30.0)
    rolling = record.get("rolling_mean_7", qty)

    narrative = (
        f"{day_name} {weekend}{holiday} with {weather} weather. "
        f"Temperature {temp:.0f}C. "
        f"Sold {qty} portions of {record.get('item_name', 'item')}. "
        f"7-day average was {rolling:.0f} portions."
    )
    return narrative