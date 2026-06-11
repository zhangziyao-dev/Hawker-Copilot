from pydantic import BaseModel
from typing import List, Optional
import json
from pathlib import Path

VENDOR_DB_PATH = "data/vendors.json"


class VendorProfile(BaseModel):
    vendor_id: str
    stall_name: str
    owner_name: str
    hawker_centre: str
    address: str
    area_type: str            # "heartland" | "cbd" | "tourist" | "suburban"
    near_mrt: bool
    mrt_station: Optional[str] = None
    near_school: bool
    school_name: Optional[str] = None
    items: List[str]
    avg_price_sgd: float
    daily_capacity: int
    operating_days: List[str]  # ["Mon","Tue","Wed","Thu","Fri"]
    telegram_chat_id: Optional[str] = None
    is_preloaded: bool = False  # True = mock vendor, False = registered


# ── 5 Preloaded Singapore Mock Vendors ───────────────────────────
PRELOADED_VENDORS: List[VendorProfile] = [
    VendorProfile(
        vendor_id="vendor_001",
        stall_name="Ah Kow Chicken Rice",
        owner_name="Mr Tan Ah Kow",
        hawker_centre="Toa Payoh Lorong 8 Market & Food Centre",
        address="Block 210 Lorong 8 Toa Payoh, Singapore 310210",
        area_type="heartland",
        near_mrt=True,
        mrt_station="Toa Payoh MRT",
        near_school=True,
        school_name="CHIJ Primary (Toa Payoh)",
        items=["Chicken Rice", "Roast Duck Rice", "Char Siew Rice"],
        avg_price_sgd=4.50,
        daily_capacity=120,
        operating_days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        telegram_chat_id=None,
        is_preloaded=True,
    ),
    VendorProfile(
        vendor_id="vendor_002",
        stall_name="Maxwell Wonton Noodle",
        owner_name="Mr Lim Wei Jie",
        hawker_centre="Maxwell Food Centre",
        address="1 Kadayanallur Street, Singapore 069184",
        area_type="tourist",
        near_mrt=True,
        mrt_station="Tanjong Pagar MRT",
        near_school=False,
        items=["Wonton Noodle", "Dumpling Soup", "Dry Noodle"],
        avg_price_sgd=5.00,
        daily_capacity=200,
        operating_days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        telegram_chat_id=None,
        is_preloaded=True,
    ),
    VendorProfile(
        vendor_id="vendor_003",
        stall_name="Chinatown Laksa Queen",
        owner_name="Mdm Siti Rahimah",
        hawker_centre="Chinatown Complex Food Centre",
        address="335 Smith Street, Singapore 050335",
        area_type="tourist",
        near_mrt=True,
        mrt_station="Chinatown MRT",
        near_school=False,
        items=["Laksa", "Mee Siam", "Prawn Mee", "Mee Rebus"],
        avg_price_sgd=5.50,
        daily_capacity=180,
        operating_days=["Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        telegram_chat_id=None,
        is_preloaded=True,
    ),
    VendorProfile(
        vendor_id="vendor_004",
        stall_name="Bedok Nasi Lemak",
        owner_name="Mr Ahmad Fauzi",
        hawker_centre="Bedok Interchange Hawker Centre",
        address="209 New Upper Changi Road, Singapore 460209",
        area_type="heartland",
        near_mrt=True,
        mrt_station="Bedok MRT",
        near_school=True,
        school_name="Bedok South Secondary School",
        items=["Nasi Lemak", "Mee Rebus", "Lontong", "Nasi Padang"],
        avg_price_sgd=4.00,
        daily_capacity=150,
        operating_days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        telegram_chat_id=None,
        is_preloaded=True,
    ),
    VendorProfile(
        vendor_id="vendor_005",
        stall_name="Jurong West Char Kway Teow",
        owner_name="Mr Ng Boon Seng",
        hawker_centre="Jurong West 505 Market & Food Centre",
        address="505 Jurong West Street 52, Singapore 640505",
        area_type="suburban",
        near_mrt=False,
        near_school=True,
        school_name="Jurong West Primary School",
        items=["Char Kway Teow", "Fried Hokkien Mee", "Oyster Omelette"],
        avg_price_sgd=4.00,
        daily_capacity=100,
        operating_days=["Mon", "Tue", "Thu", "Fri", "Sat", "Sun"],
        telegram_chat_id=None,
        is_preloaded=True,
    ),
]


def _load_vendor_db() -> List[dict]:
    """Load vendors from JSON file (registered vendors)."""
    path = Path(VENDOR_DB_PATH)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]")
    with open(path) as f:
        return json.load(f)


def _save_vendor_db(vendors: List[dict]):
    path = Path(VENDOR_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(vendors, f, indent=2, default=str)


def get_all_vendors() -> List[VendorProfile]:
    """Returns preloaded + registered vendors."""
    registered_raw = _load_vendor_db()
    registered = [VendorProfile(**v) for v in registered_raw]
    return PRELOADED_VENDORS + registered


def get_vendor_by_id(vendor_id: str) -> Optional[VendorProfile]:
    all_vendors = get_all_vendors()
    for v in all_vendors:
        if v.vendor_id == vendor_id:
            return v
    return None


def register_vendor(profile: VendorProfile) -> VendorProfile:
    """Register a new vendor (Option B — user-created)."""
    existing = _load_vendor_db()
    existing.append(profile.model_dump())
    _save_vendor_db(existing)
    return profile


def get_vendor_list_summary() -> List[dict]:
    """Lightweight list for dropdown — no sensitive fields."""
    return [
        {
            "vendor_id": v.vendor_id,
            "stall_name": v.stall_name,
            "hawker_centre": v.hawker_centre,
            "area_type": v.area_type,
            "items": v.items,
            "is_preloaded": v.is_preloaded,
        }
        for v in get_all_vendors()
    ]