from fastapi import APIRouter, HTTPException
from backend.intelligence.schemas import RetrievalQuery, RetrievalResult
from backend.intelligence.retriever import retrieve_similar_scenarios
import logging

router = APIRouter(prefix="/retrieval", tags=["retrieval"])
logger = logging.getLogger(__name__)


@router.post("/similar", response_model=RetrievalResult)
async def get_similar_scenarios(query: RetrievalQuery):
    """
    Layer 2 endpoint — retrieves historically similar demand scenarios.
    Input: forecast context. Output: top-K similar past days + stats.
    """
    try:
        result = retrieve_similar_scenarios(query, top_k=5)
        return result
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    return {"status": "ok", "layer": "intelligence-retrieval"}