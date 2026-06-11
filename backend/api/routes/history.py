from fastapi import APIRouter
from backend.database.db import get_recommendation_history

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/")
async def get_all_history(limit: int = 30):
    """Returns all recent recommendations across all vendors."""
    history = get_recommendation_history(limit=limit)
    return {"total": len(history), "history": history}


@router.get("/health")
async def health():
    return {"status": "ok", "layer": "persistence"}