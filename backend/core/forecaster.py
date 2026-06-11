import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from xgboost import XGBRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error
from datetime import date
import logging

from backend.core.feature_engineering import (
    build_features_from_history,
    build_inference_features,
    FEATURE_COLUMNS,
)
from backend.core.schemas import ForecastResult, WeatherData, ConfidenceBreakdown
from backend.core.events import get_full_event_context
from backend.config import config

logger = logging.getLogger(__name__)


def calculate_confidence(
    predicted_qty: float,
    recent_std: float,
    retrieval_avg_score: float,
    is_holiday: bool,
    is_school_holiday: bool,
    is_eve_of_holiday: bool,
    rain_probability: float,
    has_historical_match: bool,
) -> ConfidenceBreakdown:
    """
    Weighted confidence score based on signal quality.
    Returns both percentage and level with full breakdown.
    """
    # POSITIVE SIGNALS (max 100 pts)
    # 1. Retrieval quality (0-30pts) — how well history matches
    retrieval_pts = round(retrieval_avg_score * 30, 2)

    # 2. Sales stability (0-30pts) — low CV = stable = confident
    cv = (recent_std / predicted_qty) if predicted_qty > 0 else 0.5
    stability_pts = round(max(0, 30 - (cv * 60)), 2)

    # 3. Weather certainty (0-20pts) — avoid 40-60% rain uncertainty zone
    rain_uncertainty = abs(rain_probability - 0.5)
    weather_pts = round(20 * (rain_uncertainty / 0.5), 2)

    # 4. Day predictability (0-15pts)
    # Will be passed in as a calculated value
    day_pts = 15.0  # base, penalties applied below

    # 5. Lag signal (0-5pts) — placeholder, always partial
    lag_pts = 5.0

    raw_positive = retrieval_pts + stability_pts + weather_pts + day_pts + lag_pts

    # PENALTIES
    penalties = 0.0
    if not has_historical_match:
        penalties += 20
    if recent_std > predicted_qty * 0.3:
        penalties += 15
    if is_holiday:
        penalties += 12
        day_pts = max(0, day_pts - 8)
    if is_eve_of_holiday:
        penalties += 5
    if is_school_holiday:
        penalties += 5
    if 0.4 <= rain_probability <= 0.6:
        penalties += 8  # uncertainty zone penalty

    raw_score = raw_positive - penalties
    percentage = round(min(92, max(35, raw_score)), 1)

    if percentage >= 75:
        level = "HIGH"
    elif percentage >= 55:
        level = "MEDIUM"
    else:
        level = "LOW"

    return ConfidenceBreakdown(
        retrieval_quality=retrieval_pts,
        sales_stability=stability_pts,
        weather_certainty=weather_pts,
        day_predictability=day_pts,
        lag_signal=lag_pts,
        penalties=penalties,
        final_percentage=percentage,
        final_level=level,
    )


class DemandForecaster:
    def __init__(self):
        self.model = XGBRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            objective="reg:squarederror",
        )
        self.is_trained = False
        self.feature_importance: dict = {}
        self.training_stats: dict = {}

    def train(self, df: pd.DataFrame) -> dict:
        featured_df = build_features_from_history(df)
        X = featured_df[FEATURE_COLUMNS]
        y = featured_df["quantity_sold"]

        tscv = TimeSeriesSplit(n_splits=5)
        mae_scores = []

        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            self.model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
            preds = self.model.predict(X_val)
            mae_scores.append(mean_absolute_error(y_val, preds))

        self.model.fit(X, y, verbose=False)
        self.is_trained = True

        self.feature_importance = dict(
            zip(FEATURE_COLUMNS, self.model.feature_importances_.tolist())
        )
        self.training_stats = {
            "samples": len(X),
            "cv_mae_mean": round(float(np.mean(mae_scores)), 2),
            "cv_mae_std": round(float(np.std(mae_scores)), 2),
            "top_features": sorted(
                self.feature_importance.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }
        logger.info(f"Model trained. CV MAE: {self.training_stats['cv_mae_mean']:.2f}")
        return self.training_stats

    def predict(
        self,
        target_date: date,
        weather: WeatherData,
        historical_df: pd.DataFrame,
        item_name: str = "Chicken Rice",
        area_type: str = "heartland",
    ) -> ForecastResult:
        if not self.is_trained:
            raise RuntimeError("Model must be trained before prediction.")

        X_inference = build_inference_features(
            target_date, weather, historical_df, area_type
        )
        raw_pred = float(self.model.predict(X_inference[FEATURE_COLUMNS])[0])
        predicted_qty = max(0, round(raw_pred, 1))

        recent_std = float(historical_df["quantity_sold"].tail(14).std())
        lower = max(0, round(predicted_qty - 1.5 * recent_std, 1))
        upper = round(predicted_qty + 1.5 * recent_std, 1)

        top_features = dict(
            sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)[:3]
        )

        event_ctx = get_full_event_context(target_date, area_type)

        return ForecastResult(
            item_name=item_name,
            forecast_date=target_date,
            predicted_quantity=predicted_qty,
            confidence_lower=lower,
            confidence_upper=upper,
            key_features=top_features,
            model_used="xgboost-v1",
            recent_std=recent_std,
            event_context=event_ctx,
        )

    def save(self, path: str = None):
        path = path or config.MODEL_PATH
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        logger.info(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str = None) -> "DemandForecaster":
        path = path or config.MODEL_PATH
        with open(path, "rb") as f:
            return pickle.load(f)