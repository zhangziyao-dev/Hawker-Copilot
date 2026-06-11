import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta, date
from typing import Optional
from backend.config import config
from backend.core.schemas import WeatherData
import logging

logger = logging.getLogger(__name__)


# Vendor base quantities — realistic for each stall type
VENDOR_BASE_QUANTITIES = {
    "vendor_001": 80,   # heartland, 120 capacity
    "vendor_002": 130,  # CBD tourist, 200 capacity
    "vendor_003": 110,  # tourist area, 180 capacity
    "vendor_004": 95,   # heartland, 150 capacity
    "vendor_005": 65,   # suburban, 100 capacity
}

# Item-level demand ratios — main item gets most demand
ITEM_DEMAND_RATIOS = {
    "Chicken Rice":        1.00,
    "Roast Duck Rice":     0.55,
    "Char Siew Rice":      0.45,
    "Wonton Noodle":       1.00,
    "Dumpling Soup":       0.50,
    "Dry Noodle":          0.40,
    "Laksa":               1.00,
    "Mee Siam":            0.60,
    "Prawn Mee":           0.55,
    "Mee Rebus":           0.45,
    "Nasi Lemak":          1.00,
    "Lontong":             0.50,
    "Nasi Padang":         0.45,
    "Char Kway Teow":      1.00,
    "Fried Hokkien Mee":   0.65,
    "Oyster Omelette":     0.45,
}

def generate_synthetic_pos_data(
    item_name: str = "Chicken Rice",
    days: int = 180,
    base_quantity: int = None,
    vendor_id: str = None,
) -> pd.DataFrame:
    """
    Generates realistic vendor-specific POS data.
    Each vendor has different base demand reflecting
    their location, capacity and customer profile.
    """
    # Resolve base quantity from vendor or item ratio
    if base_quantity is None:
        vendor_base = VENDOR_BASE_QUANTITIES.get(vendor_id, 80)
        item_ratio = ITEM_DEMAND_RATIOS.get(item_name, 1.0)
        base_quantity = max(20, int(vendor_base * item_ratio))

    np.random.seed(
        abs(hash(f"{vendor_id}_{item_name}")) % (2**31)
    )

    dates = [datetime.today() - timedelta(days=i) for i in range(days, 0, -1)]
    records = []

    for d in dates:
        dow = d.weekday()

        is_weekend = 1.25 if dow >= 5 else 1.0
        is_friday  = 1.15 if dow == 4 else 1.0
        is_monday  = 0.85 if dow == 0 else 1.0

        rained = np.random.random() < 0.30
        rain_effect = 0.75 if rained else 1.0

        is_holiday = np.random.random() < 0.05
        holiday_effect = 1.35 if is_holiday else 1.0

        quantity = int(
            base_quantity
            * is_weekend * is_friday * is_monday
            * rain_effect * holiday_effect
            * np.random.normal(1.0, 0.08)
        )
        quantity = max(5, quantity)

        records.append({
            "date":          d.date(),
            "item_name":     item_name,
            "quantity_sold": quantity,
            "revenue":       round(quantity * 4.50, 2),
            "rained":        rained,
            "is_holiday":    is_holiday,
            "day_of_week":   dow,
        })

    return pd.DataFrame(records)


def load_pos_data(
    filepath: str = None,
    item_name: str = "Chicken Rice",
    vendor_id: str = None,
) -> pd.DataFrame:
    if filepath:
        try:
            df = pd.read_csv(filepath, parse_dates=["date"])
            df["date"] = df["date"].dt.date
            return df
        except Exception as e:
            logger.warning(f"CSV load failed: {e}. Using synthetic.")

    return generate_synthetic_pos_data(
        item_name=item_name,
        vendor_id=vendor_id,
    )


def fetch_weather_forecast(target_date: date, city: str = "Singapore") -> WeatherData:
    """
    Fetch weather from OpenWeatherMap. Falls back to synthetic if no API key.
    """
    if not config.WEATHER_API_KEY:
        return _synthetic_weather(target_date)

    try:
        url = f"{config.WEATHER_BASE_URL}/forecast"
        params = {
            "q": city,
            "appid": config.WEATHER_API_KEY,
            "units": "metric",
            "cnt": 8,
        }
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        # Take first forecast period
        forecast = data["list"][0]
        return WeatherData(
            date=target_date,
            temperature=forecast["main"]["temp"],
            humidity=forecast["main"]["humidity"],
            weather_condition=forecast["weather"][0]["main"].lower(),
            rain_probability=forecast.get("pop", 0.0),
        )
    except Exception as e:
        logger.warning(f"Weather API failed: {e}. Using synthetic weather.")
        return _synthetic_weather(target_date)


def _synthetic_weather(target_date: date) -> WeatherData:
    """Deterministic synthetic weather based on day seed."""
    np.random.seed(target_date.toordinal() % 1000)
    rain_prob = round(float(np.random.uniform(0.1, 0.9)), 2)
    return WeatherData(
        date=target_date,
        temperature=round(float(np.random.uniform(26, 34)), 1),
        humidity=round(float(np.random.uniform(60, 90)), 1),
        weather_condition="rain" if rain_prob > 0.6 else "clear",
        rain_probability=rain_prob,
    )