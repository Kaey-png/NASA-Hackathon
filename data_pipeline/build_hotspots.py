"""Create state-level drought and flood estimates from model forecasts."""
from pathlib import Path

import numpy as np
import pandas as pd

from config import HOTSPOTS_PATH, STATES
from data_pipeline.build_dataset import (
    PRECIPITATION_COLUMN,
    SOIL_COLUMNS,
    TEMPERATURE_COLUMN,
)
from ml.nasa_model import (
    APP_DIR,
    CLEANED_DIR,
    STATE_FOLDERS,
    TEST_PREDICTIONS_PATH,
    forecast_monthly,
)


FORECAST_PATH = APP_DIR / "data" / "processed" / "model_forecast.csv"
LOW_QUANTILE = 0.20
HIGH_QUANTILE = 0.80
MIN_CLIMATOLOGY_MONTHS = 10
MIN_VALIDATION_ERRORS = 12
DROUGHT_FACTORS = (TEMPERATURE_COLUMN, PRECIPITATION_COLUMN, *SOIL_COLUMNS)


def _threshold(history, factor, month, quantile):
    values = pd.to_numeric(
        history.loc[history["date"].dt.month == month, factor],
        errors="coerce",
    ).dropna()
    if len(values) < MIN_CLIMATOLOGY_MONTHS:
        raise ValueError(
            f"Not enough month-{month} observations for {factor}: {len(values)}"
        )
    return float(values.quantile(quantile))


def _errors(validation, state, factor):
    rows = validation[
        (validation["state"] == state)
        & (validation["factor"] == factor)
    ]
    errors = (rows["actual"] - rows["predicted"]).dropna().to_numpy(dtype=float)
    if len(errors) < MIN_VALIDATION_ERRORS:
        raise ValueError(
            f"Not enough held-out model errors for {state}/{factor}: {len(errors)}"
        )
    return errors


def _tail_probability(predicted, errors, threshold, upper_tail):
    simulated_values = predicted + errors
    if upper_tail:
        return float(np.mean(simulated_values >= threshold))
    return float(np.mean(simulated_values <= threshold))


def make_phenomena_predictions(forecasts, histories, validation, states=STATES):
    state_config = {state["name"]: state for state in states}
    forecast_groups = forecasts.groupby(["state", "date"], sort=True)
    rows = []

    for (state, date), group in forecast_groups:
        if state not in state_config or state not in histories:
            raise ValueError(f"Missing state configuration or history for {state}")
        predicted = group.set_index("factor")["predicted_value"].to_dict()
        missing = set(DROUGHT_FACTORS) - set(predicted)
        if missing:
            raise ValueError(f"Forecast for {state} is missing factors: {sorted(missing)}")
        history = histories[state]
        month = pd.Timestamp(date).month

        drought_signals = [
            _tail_probability(
                predicted[TEMPERATURE_COLUMN],
                _errors(validation, state, TEMPERATURE_COLUMN),
                _threshold(history, TEMPERATURE_COLUMN, month, HIGH_QUANTILE),
                upper_tail=True,
            ),
            _tail_probability(
                predicted[PRECIPITATION_COLUMN],
                _errors(validation, state, PRECIPITATION_COLUMN),
                _threshold(history, PRECIPITATION_COLUMN, month, LOW_QUANTILE),
                upper_tail=False,
            ),
        ]
        flood_signals = [
            _tail_probability(
                predicted[PRECIPITATION_COLUMN],
                _errors(validation, state, PRECIPITATION_COLUMN),
                _threshold(history, PRECIPITATION_COLUMN, month, HIGH_QUANTILE),
                upper_tail=True,
            ),
        ]
        soil_drought, soil_flood = [], []
        for factor in SOIL_COLUMNS:
            error_values = _errors(validation, state, factor)
            soil_drought.append(_tail_probability(
                predicted[factor],
                error_values,
                _threshold(history, factor, month, LOW_QUANTILE),
                upper_tail=False,
            ))
            soil_flood.append(_tail_probability(
                predicted[factor],
                error_values,
                _threshold(history, factor, month, HIGH_QUANTILE),
                upper_tail=True,
            ))

        drought_signals.append(float(np.mean(soil_drought)))
        flood_signals.append(float(np.mean(soil_flood)))
        state_info = state_config[state]
        rows.extend([
            {
                "state": state_info["code"],
                "lat": state_info["view"]["lat"],
                "lon": state_info["view"]["lon"],
                "phenomenon": "drought",
                "probability": round(float(np.mean(drought_signals)), 4),
                "for_month": pd.Timestamp(date),
            },
            {
                "state": state_info["code"],
                "lat": state_info["view"]["lat"],
                "lon": state_info["view"]["lon"],
                "phenomenon": "flood",
                "probability": round(float(np.mean(flood_signals)), 4),
                "for_month": pd.Timestamp(date),
            },
        ])

    return pd.DataFrame(rows)


def _load_histories(cleaned_dir=CLEANED_DIR):
    histories = {}
    for state, folder in STATE_FOLDERS.items():
        path = Path(cleaned_dir) / folder / f"{folder}_clean.csv"
        history = pd.read_csv(path, parse_dates=["date"])
        histories[state] = history
    return histories


def build():
    forecasts = forecast_monthly()
    validation = pd.read_csv(TEST_PREDICTIONS_PATH)
    histories = _load_histories()
    predictions = make_phenomena_predictions(forecasts, histories, validation)

    FORECAST_PATH.parent.mkdir(parents=True, exist_ok=True)
    forecasts.to_csv(FORECAST_PATH, index=False, date_format="%Y-%m-%d")
    predictions.to_csv(HOTSPOTS_PATH, index=False, date_format="%Y-%m-%d")
    print(f"Wrote {len(forecasts)} model forecasts to {FORECAST_PATH}")
    print(f"Wrote {len(predictions)} state-level phenomena estimates to {HOTSPOTS_PATH}")
    return forecasts, predictions


if __name__ == "__main__":
    build()
