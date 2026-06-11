import pandas as pd
import numpy as np
from datetime import date
from backend.core.schemas import WeatherData
from backend.core.events import (
    get_full_event_context,
    is_public_holiday,
    is_school_holiday,
    is_payday_period,
    is_monsoon_season,
    is_eve_of_holiday,
    is_day_after_holiday,
)

# Extended feature columns — includes all new SG-specific flags
FEATURE_COLUMNS = [
    "day_of_week", "month", "day_of_month", "is_weekend", "is_friday",
    "is_monday", "week_of_year",
    "is_holiday", "is_eve_of_holiday", "is_day_after_holiday",
    "is_school_holiday", "is_payday_period", "is_monsoon_season",
    "rain_flag", "temperature", "humidity",
    "lag_1", "lag_7", "rolling_mean_7", "rolling_std_7",
]


def build_features_from_history(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # Temporal features
    df["day_of_week"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["day_of_month"] = df["date"].dt.day
    df["is_weekend"] = (df["date"].dt.dayofweek >= 5).astype(int)
    df["is_friday"] = (df["date"].dt.dayofweek == 4).astype(int)
    df["is_monday"] = (df["date"].dt.dayofweek == 0).astype(int)
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)

    # SG-specific event flags
    df["is_holiday"] = df["date"].dt.date.apply(
        lambda d: int(is_public_holiday(d)[0])
    )
    df["is_eve_of_holiday"] = df["date"].dt.date.apply(
        lambda d: int(is_eve_of_holiday(d))
    )
    df["is_day_after_holiday"] = df["date"].dt.date.apply(
        lambda d: int(is_day_after_holiday(d))
    )
    df["is_school_holiday"] = df["date"].dt.date.apply(
        lambda d: int(is_school_holiday(d)[0])
    )
    df["is_payday_period"] = df["date"].dt.date.apply(
        lambda d: int(is_payday_period(d))
    )
    df["is_monsoon_season"] = df["date"].dt.date.apply(
        lambda d: int(is_monsoon_season(d))
    )

    # Weather
    if "rained" in df.columns:
        df["rain_flag"] = df["rained"].astype(int)
    else:
        df["rain_flag"] = 0
    if "temperature" not in df.columns:
        df["temperature"] = 30.0
    if "humidity" not in df.columns:
        df["humidity"] = 75.0

    # Lag features
    df["lag_1"] = df["quantity_sold"].shift(1)
    df["lag_7"] = df["quantity_sold"].shift(7)
    df["rolling_mean_7"] = df["quantity_sold"].shift(1).rolling(7).mean()
    df["rolling_std_7"] = df["quantity_sold"].shift(1).rolling(7).std()

    df.dropna(inplace=True)
    return df


def build_inference_features(
    target_date: date,
    weather: WeatherData,
    historical_df: pd.DataFrame,
    area_type: str = "heartland",
) -> pd.DataFrame:
    d = pd.Timestamp(target_date)
    dow = d.dayofweek

    hist_sorted = historical_df.copy()
    hist_sorted["date"] = pd.to_datetime(hist_sorted["date"])
    hist_sorted = hist_sorted.sort_values("date")
    recent_sales = hist_sorted["quantity_sold"].values

    lag_1 = float(recent_sales[-1]) if len(recent_sales) >= 1 else 80.0
    lag_7 = float(recent_sales[-7]) if len(recent_sales) >= 7 else 80.0
    rolling_mean_7 = float(np.mean(recent_sales[-7:])) if len(recent_sales) >= 7 else 80.0
    rolling_std_7 = float(np.std(recent_sales[-7:])) if len(recent_sales) >= 7 else 5.0

    # Get all SG event context
    event_ctx = get_full_event_context(target_date, area_type)

    features = {
        "day_of_week":          int(dow),
        "month":                int(d.month),
        "day_of_month":         int(d.day),
        "is_weekend":           int(dow >= 5),
        "is_friday":            int(dow == 4),
        "is_monday":            int(dow == 0),
        "week_of_year":         int(d.isocalendar()[1]),
        "is_holiday":           int(event_ctx["is_public_holiday"]),
        "is_eve_of_holiday":    int(event_ctx["is_eve_of_holiday"]),
        "is_day_after_holiday": int(event_ctx["is_day_after_holiday"]),
        "is_school_holiday":    int(event_ctx["is_school_holiday"]),
        "is_payday_period":     int(event_ctx["is_payday_period"]),
        "is_monsoon_season":    int(event_ctx["is_monsoon_season"]),
        "rain_flag":            int(weather.rain_probability > 0.6),
        "temperature":          float(weather.temperature),
        "humidity":             float(weather.humidity),
        "lag_1":                lag_1,
        "lag_7":                lag_7,
        "rolling_mean_7":       rolling_mean_7,
        "rolling_std_7":        rolling_std_7,
    }

    df = pd.DataFrame([features])
    return df[FEATURE_COLUMNS]