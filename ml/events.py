"""Estimate next-month extreme-event chances from model forecasts and errors."""
import numpy as np
import pandas as pd


LOW_QUANTILE = 0.20
HIGH_QUANTILE = 0.80
MIN_HISTORY_MONTHS = 120
MIN_VALIDATION_ERRORS = 12
LOW_CONFIDENCE_ERRORS = 30


def _month_values(history, month):
    return history.loc[history["date"].dt.month == month, "value"].to_numpy(dtype=float)


def model_event_chances(df, prediction, for_month, errors, scale=1):
    """Combine a model forecast with held-out residuals and month-specific thresholds."""
    history = df[["date", "value"]].copy()
    history["date"] = pd.to_datetime(history["date"], errors="coerce")
    history["value"] = pd.to_numeric(history["value"], errors="coerce")
    history = (
        history.dropna(subset=["date", "value"])
        .sort_values("date")
        .reset_index(drop=True)
    )
    if len(history) < MIN_HISTORY_MONTHS:
        return None
    if history["date"].duplicated().any():
        raise ValueError("Event history must contain at most one value per month")

    scale = float(scale)
    prediction = float(prediction) * scale
    for_month = pd.Timestamp(for_month)
    if not np.isfinite(scale) or scale <= 0 or not np.isfinite(prediction) or pd.isna(for_month):
        raise ValueError("The model prediction, scale, and forecast month must be valid")

    residuals = np.asarray(errors, dtype=float) * scale
    residuals = residuals[np.isfinite(residuals)]
    if len(residuals) < MIN_VALIDATION_ERRORS:
        return None

    prior = history.iloc[:-1]
    target_values = _month_values(prior, for_month.month)
    if len(target_values) < 5:
        return None
    low, high = np.quantile(target_values, [LOW_QUANTILE, HIGH_QUANTILE])
    simulated = prediction + residuals
    normal_low = float(np.mean(target_values <= low))
    normal_high = float(np.mean(target_values >= high))

    latest = history.iloc[-1]
    latest_values = _month_values(prior, latest["date"].month)
    if len(latest_values) < 5:
        current = 0
    else:
        current_low, current_high = np.quantile(
            latest_values, [LOW_QUANTILE, HIGH_QUANTILE]
        )
        current = (
            -1 if latest["value"] <= current_low
            else 1 if latest["value"] >= current_high
            else 0
        )

    return {
        "model": "NASA environmental AI model with held-out forecast errors",
        "as_of": latest["date"],
        "for_month": for_month,
        "history_months": len(history),
        "current": current,
        "events": [
            {
                "key": "low",
                "probability": float(np.mean(simulated <= low)),
                "normal_rate": normal_low,
                "skill": None,
                "matches": len(residuals),
                "low_confidence": len(residuals) < LOW_CONFIDENCE_ERRORS,
            },
            {
                "key": "high",
                "probability": float(np.mean(simulated >= high)),
                "normal_rate": normal_high,
                "skill": None,
                "matches": len(residuals),
                "low_confidence": len(residuals) < LOW_CONFIDENCE_ERRORS,
            },
        ],
    }
