from fastapi import APIRouter, HTTPException
from backend.core.vendor_profiles import (
    get_all_vendors, get_vendor_by_id,
    register_vendor, get_vendor_list_summary,
    VendorProfile,
)
from backend.database.db import get_recommendation_history
from typing import List
import uuid

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("/", response_model=List[dict])
async def list_vendors():
    """
    Returns lightweight vendor list for frontend dropdown.
    Includes both preloaded and registered vendors.
    """
    return get_vendor_list_summary()


@router.get("/{vendor_id}")
async def get_vendor(vendor_id: str):
    """Returns full vendor profile by ID."""
    vendor = get_vendor_by_id(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
    return vendor


@router.post("/register")
async def register_new_vendor(profile: dict):
    """
    Option B — vendor self-registration.
    Creates new vendor profile and saves to vendors.json
    """
    try:
        vendor_id = f"vendor_{uuid.uuid4().hex[:8]}"
        vendor = VendorProfile(
            vendor_id=vendor_id,
            stall_name=profile["stall_name"],
            owner_name=profile.get("owner_name", ""),
            hawker_centre=profile["hawker_centre"],
            address=profile.get("address", ""),
            area_type=profile.get("area_type", "heartland"),
            near_mrt=profile.get("near_mrt", False),
            mrt_station=profile.get("mrt_station"),
            near_school=profile.get("near_school", False),
            school_name=profile.get("school_name"),
            items=profile.get("items", []),
            avg_price_sgd=float(profile.get("avg_price_sgd", 4.50)),
            daily_capacity=int(profile.get("daily_capacity", 100)),
            operating_days=profile.get("operating_days", ["Mon","Tue","Wed","Thu","Fri"]),
            telegram_chat_id=profile.get("telegram_chat_id"),
            is_preloaded=False,
        )
        register_vendor(vendor)
        return {"status": "registered", "vendor_id": vendor_id, "stall_name": vendor.stall_name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{vendor_id}/history")
async def get_vendor_history(vendor_id: str, limit: int = 14):
    """Returns past recommendations for a specific vendor."""
    history = get_recommendation_history(vendor_id=vendor_id, limit=limit)
    if not history:
        return {"vendor_id": vendor_id, "history": [], "message": "No history yet"}
    return {"vendor_id": vendor_id, "history": history}