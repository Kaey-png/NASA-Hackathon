import numpy as np
import pandas as pd

from data_pipeline.build_dataset import (
    PRECIPITATION_COLUMN,
    SOIL_COLUMNS,
    TEMPERATURE_COLUMN,
)
from data_pipeline.build_hotspots import make_phenomena_predictions


def test_phenomena_estimates_use_model_errors_and_state_centers():
    dates = pd.date_range("2000-01-01", periods=240, freq="MS")
    history = pd.DataFrame({"date": dates})
    for index, factor in enumerate((TEMPERATURE_COLUMN, PRECIPITATION_COLUMN, *SOIL_COLUMNS)):
        history[factor] = np.arange(len(dates), dtype=float) + index

    month = 1
    month_history = history[history.date.dt.month == month]
    predicted = {}
    for factor in (TEMPERATURE_COLUMN, PRECIPITATION_COLUMN, *SOIL_COLUMNS):
        values = month_history[factor].to_numpy()
        predicted[factor] = float(values[-1] + 100)
    predicted[PRECIPITATION_COLUMN] = float(
        month_history[PRECIPITATION_COLUMN].quantile(0.2) - 100
    )
    for factor in SOIL_COLUMNS:
        predicted[factor] = float(month_history[factor].quantile(0.2) - 100)

    forecasts = pd.DataFrame([
        {
            "date": pd.Timestamp("2027-01-01"),
            "state": "Alabama",
            "factor": factor,
            "predicted_value": value,
        }
        for factor, value in predicted.items()
    ])
    validation = pd.DataFrame([
        {"state": "Alabama", "factor": factor, "actual": e, "predicted": 0.0}
        for factor in (TEMPERATURE_COLUMN, PRECIPITATION_COLUMN, *SOIL_COLUMNS)
        for e in np.linspace(-1, 1, 20)
    ])

    result = make_phenomena_predictions(
        forecasts,
        {"Alabama": history},
        validation,
        states=[{
            "name": "Alabama",
            "code": "AL",
            "view": {"lat": 32.8, "lon": -86.8},
        }],
    )

    drought = result[result.phenomenon == "drought"].iloc[0]
    flood = result[result.phenomenon == "flood"].iloc[0]
    assert len(result) == 2
    assert drought.probability > flood.probability
    assert drought.state == "AL" and drought.lat == 32.8 and drought.lon == -86.8
    assert result.probability.between(0, 1).all()


if __name__ == "__main__":
    test_phenomena_estimates_use_model_errors_and_state_centers()
