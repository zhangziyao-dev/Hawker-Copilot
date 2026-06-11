from datetime import date
from typing import Optional


# ── Singapore Public Holidays 2024-2026 ──────────────────────────
SG_PUBLIC_HOLIDAYS = {
    # 2024
    date(2024, 1, 1):  "New Year's Day",
    date(2024, 2, 10): "Chinese New Year Day 1",
    date(2024, 2, 11): "Chinese New Year Day 2",
    date(2024, 4, 10): "Good Friday",
    date(2024, 5, 1):  "Labour Day",
    date(2024, 5, 22): "Vesak Day",
    date(2024, 6, 17): "Hari Raya Haji",
    date(2024, 8, 9):  "National Day",
    date(2024, 10, 31):"Deepavali",
    date(2024, 12, 25):"Christmas Day",
    # 2025
    date(2025, 1, 1):  "New Year's Day",
    date(2025, 1, 29): "Chinese New Year Day 1",
    date(2025, 1, 30): "Chinese New Year Day 2",
    date(2025, 3, 31): "Hari Raya Puasa",
    date(2025, 4, 18): "Good Friday",
    date(2025, 5, 1):  "Labour Day",
    date(2025, 5, 12): "Vesak Day",
    date(2025, 6, 7):  "Hari Raya Haji",
    date(2025, 8, 9):  "National Day",
    date(2025, 10, 20):"Deepavali",
    date(2025, 12, 25):"Christmas Day",
    # 2026
    date(2026, 1, 1):  "New Year's Day",
    date(2026, 1, 19): "Chinese New Year Day 1",
    date(2026, 1, 20): "Chinese New Year Day 2",
    date(2026, 3, 20): "Hari Raya Puasa",
    date(2026, 4, 3):  "Good Friday",
    date(2026, 5, 1):  "Labour Day",
    date(2026, 5, 31): "Vesak Day",
    date(2026, 5, 27): "Hari Raya Haji",
    date(2026, 8, 9):  "National Day",
    date(2026, 11, 8): "Deepavali",
    date(2026, 12, 25):"Christmas Day",
}

# ── Singapore School Holidays 2025-2026 ──────────────────────────
SG_SCHOOL_HOLIDAYS = [
    # 2025
    (date(2025, 3, 15), date(2025, 3, 23), "March School Holidays"),
    (date(2025, 5, 31), date(2025, 6, 29), "June School Holidays"),
    (date(2025, 8, 30), date(2025, 9, 7),  "September School Holidays"),
    (date(2025, 11, 15),date(2026, 1, 1),  "Year-End School Holidays"),
    # 2026
    (date(2026, 3, 14), date(2026, 3, 22), "March School Holidays"),
    (date(2026, 5, 30), date(2026, 6, 28), "June School Holidays"),
    (date(2026, 8, 29), date(2026, 9, 6),  "September School Holidays"),
    (date(2026, 11, 21),date(2027, 1, 1),  "Year-End School Holidays"),
]

# ── Major Singapore Events (simulated, expandable) ───────────────
SG_MAJOR_EVENTS = [
    {
        "name": "Singapore Grand Prix",
        "start": date(2025, 9, 19),
        "end": date(2025, 9, 21),
        "demand_multiplier": 1.35,
        "affected_areas": ["cbd", "tourist"],
    },
    {
        "name": "Chinese New Year Period",
        "start": date(2025, 1, 25),
        "end": date(2025, 2, 2),
        "demand_multiplier": 0.6,
        "affected_areas": ["all"],
        "note": "Many stalls closed, reduced crowd",
    },
    {
        "name": "Great Singapore Sale",
        "start": date(2025, 6, 1),
        "end": date(2025, 7, 31),
        "demand_multiplier": 1.1,
        "affected_areas": ["tourist", "cbd"],
    },
    {
        "name": "National Day Parade Period",
        "start": date(2025, 8, 7),
        "end": date(2025, 8, 10),
        "demand_multiplier": 1.3,
        "affected_areas": ["cbd", "tourist"],
    },
    {
        "name": "Deepavali Festival Period",
        "start": date(2025, 10, 17),
        "end": date(2025, 10, 22),
        "demand_multiplier": 1.2,
        "affected_areas": ["heartland", "tourist"],
    },
]


def is_public_holiday(d: date) -> tuple[bool, Optional[str]]:
    name = SG_PUBLIC_HOLIDAYS.get(d)
    return (name is not None), name


def is_eve_of_holiday(d: date) -> bool:
    """Day before a public holiday — often busier than normal."""
    from datetime import timedelta
    next_day = d + timedelta(days=1)
    return next_day in SG_PUBLIC_HOLIDAYS


def is_day_after_holiday(d: date) -> bool:
    """Day after public holiday — slower return to normal."""
    from datetime import timedelta
    prev_day = d - timedelta(days=1)
    return prev_day in SG_PUBLIC_HOLIDAYS


def is_school_holiday(d: date) -> tuple[bool, Optional[str]]:
    for start, end, name in SG_SCHOOL_HOLIDAYS:
        if start <= d <= end:
            return True, name
    return False, None


def is_payday_period(d: date) -> bool:
    """
    Last 3 days + first 2 days of month = payday effect.
    Singapore salaried workers paid end of month.
    """
    return d.day >= 25 or d.day <= 2


def is_monsoon_season(d: date) -> bool:
    """
    Northeast monsoon: Nov-Jan (heavy rain)
    Southwest monsoon: Jun-Sep (moderate rain)
    """
    return d.month in [11, 12, 1, 6, 7, 8, 9]


def get_nearby_event(d: date, area_type: str = "all") -> Optional[dict]:
    """Returns active major event for a date and area type."""
    for event in SG_MAJOR_EVENTS:
        if event["start"] <= d <= event["end"]:
            affected = event.get("affected_areas", ["all"])
            if "all" in affected or area_type in affected:
                return event
    return None


def get_full_event_context(d: date, area_type: str = "heartland") -> dict:
    """
    Master function — returns all event context for a date.
    Used by feature engineering and confidence calculator.
    """
    is_ph, ph_name = is_public_holiday(d)
    is_sh, sh_name = is_school_holiday(d)
    nearby_event = get_nearby_event(d, area_type)

    return {
        "is_public_holiday": is_ph,
        "public_holiday_name": ph_name,
        "is_eve_of_holiday": is_eve_of_holiday(d),
        "is_day_after_holiday": is_day_after_holiday(d),
        "is_school_holiday": is_sh,
        "school_holiday_name": sh_name,
        "is_payday_period": is_payday_period(d),
        "is_monsoon_season": is_monsoon_season(d),
        "nearby_event": nearby_event,
        "nearby_event_name": nearby_event["name"] if nearby_event else None,
        "event_demand_multiplier": nearby_event["demand_multiplier"] if nearby_event else 1.0,
    }