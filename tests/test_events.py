import numpy as np
import pandas as pd

import app as app_module
from core.interpret import build_event_response
from data_pipeline.build_dataset import (
    PRECIPITATION_COLUMN,
    TEMPERATURE_COLUMN,
)
from ml.events import model_event_chances


def _history():
    dates = pd.date_range("2000-01-01", periods=240, freq="MS")
    values = np.array([
        20 + index // 12 + dates[index].month / 100
        for index in range(len(dates))
    ])
    return pd.DataFrame({"date": dates, "value": values})


def test_model_forecast_drives_low_and_high_event_chances():
    history = _history()
    errors = np.linspace(-0.1, 0.1, 40)

    low = model_event_chances(history, -100, "2020-01-01", errors)
    high = model_event_chances(history, 100, "2020-01-01", errors)

    assert low["events"][0]["probability"] == 1
    assert low["events"][1]["probability"] == 0
    assert high["events"][0]["probability"] == 0
    assert high["events"][1]["probability"] == 1
    assert low["events"][0]["normal_rate"] < 0.3
    assert "NASA environmental AI model" in low["model"]


def test_soil_moisture_prediction_and_errors_are_scaled_to_app_units():
    result = model_event_chances(
        _history(),
        prediction=0.38,
        for_month="2020-01-01",
        errors=np.linspace(-0.01, 0.01, 40),
        scale=100,
    )

    assert result["events"][1]["probability"] == 1
    assert result["events"][0]["probability"] == 0


def test_model_event_chances_require_sufficient_history_and_validation_errors():
    assert model_event_chances(
        _history().tail(24), 0, "2020-01-01", np.zeros(40)
    ) is None
    assert model_event_chances(
        _history(), 0, "2020-01-01", np.zeros(5)
    ) is None


def test_temperature_event_response_has_hot_and_cool_labels():
    result = {
        "model": "NASA environmental AI model with held-out forecast errors",
        "as_of": pd.Timestamp("2020-12-01"),
        "for_month": pd.Timestamp("2021-01-01"),
        "history_months": 240,
        "current": 0,
        "events": [
            {"key": "low", "probability": 0.1, "normal_rate": 0.2,
             "skill": None, "low_confidence": False},
            {"key": "high", "probability": 0.8, "normal_rate": 0.2,
             "skill": None, "low_confidence": False},
        ],
    }

    response = build_event_response(result, "temperature", "Alabama", "MERRA-2")

    assert response["events"][0]["label"] == "Unusually hot month"
    assert response["events"][1]["label"] == "Unusually cool month"
    assert "model forecast and held-out model errors" in response["basis"]


def test_event_chance_api_uses_saved_model_forecasts(monkeypatch):
    state_name = "Alabama"
    state_code = "AL"
    month = pd.Timestamp.today().to_period("M").to_timestamp()
    factors = {
        "temperature": TEMPERATURE_COLUMN,
        "precipitation": PRECIPITATION_COLUMN,
        "soil_moisture": "FLDAS_0-10cm",
    }
    forecasts = pd.DataFrame([
        {"state": state_name, "factor": factor, "date": month,
         "predicted_value": 100.0 if factor != "FLDAS_0-10cm" else 0.5}
        for factor in factors.values()
    ])
    validation = pd.DataFrame([
        {"state": state_name, "factor": factor, "actual": 1.0, "predicted": 0.0}
        for factor in factors.values()
        for _ in range(40)
    ])
    monkeypatch.setattr(
        app_module, "_load_model_event_data", lambda: (forecasts, validation)
    )

    for variable, factor in factors.items():
        app_module._event_cache.clear()
        depth = "&depth=0-10cm" if variable == "soil_moisture" else ""
        response = app_module.app.test_client().get(
            f"/api/event-chance?state={state_code}&variable={variable}{depth}"
        )
        body = response.get_json()

        assert response.status_code == 200
        assert body["available"]
        assert body["for_month"] == month.strftime("%B %Y")
        assert "NASA environmental AI model" in body["basis"]
        assert len(body["events"]) == 2

