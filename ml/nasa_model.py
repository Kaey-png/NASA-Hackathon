"""Inference helpers for the trained NASA multi-output environmental model."""
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn


APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parent
NASA_RESULTS_DIR = (
    REPO_ROOT
    / "NASA_Hackathon"
    / "DataAnalysis"
    / "Cleaned"
    / "Unified"
    / "Integrated_AI_Results"
)
BUNDLED_MODEL_DIR = APP_DIR / "data" / "models"
CLEANED_DIR = APP_DIR / "data" / "cleaned"
STATE_FOLDERS = {
    "Alabama": "Alabama",
    "New York": "NewYork",
    "Texas": "Texas",
}


def _artifact_path(name):
    repository_file = NASA_RESULTS_DIR / name
    if repository_file.is_file():
        return repository_file
    return BUNDLED_MODEL_DIR / name


MODEL_PATH = _artifact_path("environmental_ai_model.pth")
TEST_PREDICTIONS_PATH = _artifact_path("historical_test_predictions.csv")


class EnvironmentalNetwork(nn.Module):
    def __init__(self, input_size, output_size):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.10),
            nn.Linear(64, output_size),
        )

    def forward(self, inputs):
        return self.network(inputs)


def _load_checkpoint(path):
    numpy_core = getattr(np, "_core", np.core)
    safe_numpy_types = [
        numpy_core.multiarray._reconstruct,
        np.ndarray,
        np.dtype,
        type(np.dtype(np.float64)),
    ]
    with torch.serialization.safe_globals(safe_numpy_types):
        return torch.load(path, map_location="cpu", weights_only=True)


def load_cleaned_panels(states, factors, cleaned_dir=CLEANED_DIR):
    cleaned_dir = Path(cleaned_dir)
    raw_panels = {}
    for state in states:
        folder = STATE_FOLDERS.get(state)
        if folder is None:
            raise ValueError(f"No cleaned input file is configured for model state {state!r}")
        path = cleaned_dir / folder / f"{folder}_clean.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Cleaned input file not found: {path}")
        data = pd.read_csv(path, parse_dates=["date"])
        missing = [factor for factor in factors if factor not in data.columns]
        if missing:
            raise ValueError(f"{path} is missing model factors: {missing}")
        if data["date"].isna().any() or data["date"].duplicated().any():
            raise ValueError(f"{path} must have unique, valid monthly dates")
        raw_panels[state] = data.set_index("date")[list(factors)].apply(
            pd.to_numeric, errors="coerce"
        )

    first_date = min(panel.index.min() for panel in raw_panels.values())
    last_date = max(panel.index.max() for panel in raw_panels.values())
    dates = pd.date_range(first_date, last_date, freq="MS")
    panels = {
        state: panel.reindex(index=dates, columns=factors)
        for state, panel in raw_panels.items()
    }
    return dates, panels


def forecast_monthly(model_path=MODEL_PATH, cleaned_dir=CLEANED_DIR):
    checkpoint = _load_checkpoint(model_path)
    factors = list(checkpoint["factors"])
    states = list(checkpoint["states"])
    lookback = int(checkpoint["lookback"])
    means = np.asarray(checkpoint["means"], dtype=np.float64)
    stds = np.asarray(checkpoint["stds"], dtype=np.float64)
    if len(factors) != len(means) or len(factors) != len(stds):
        raise ValueError("Model factor and normalization dimensions do not match")

    dates, panels = load_cleaned_panels(states, factors, cleaned_dir)
    if len(dates) < lookback:
        raise ValueError(f"Need at least {lookback} months of cleaned history")

    input_size = 2 * lookback * len(factors) + len(states) + 2
    model = EnvironmentalNetwork(input_size, len(factors))
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    state_indices = {state: index for index, state in enumerate(states)}
    forecast_rows = []
    latest_date = dates[-1]

    for state, panel in panels.items():
        history = panel.to_numpy(dtype=np.float64).copy()
        state_vector = np.zeros(len(states), dtype=np.float32)
        state_vector[state_indices[state]] = 1.0

        for step in range(12):
            recent = history[-lookback:]
            missing = np.isnan(recent)
            normalized = (recent - means) / stds
            normalized = np.nan_to_num(normalized, nan=0.0)
            next_date = latest_date + pd.DateOffset(months=step + 1)
            month = next_date.month
            calendar = np.array([
                np.sin(2 * np.pi * month / 12),
                np.cos(2 * np.pi * month / 12),
            ], dtype=np.float32)
            model_input = np.concatenate([
                normalized.flatten(),
                missing.astype(np.float32).flatten(),
                state_vector,
                calendar,
            ])

            with torch.no_grad():
                normalized_prediction = model(
                    torch.tensor(model_input, dtype=torch.float32).unsqueeze(0)
                ).numpy()[0]
            prediction = normalized_prediction * stds + means
            if not np.isfinite(prediction).all():
                raise ValueError(f"Model returned a non-finite forecast for {state}")

            forecast_rows.extend({
                "date": next_date,
                "state": state,
                "factor": factor,
                "predicted_value": float(prediction[index]),
            } for index, factor in enumerate(factors))
            history = np.vstack([history, prediction])

    return pd.DataFrame(forecast_rows)
