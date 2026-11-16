import pandas as pd
from flask import Flask, jsonify, render_template, request

from config import PARAMETERS, PHENOMENA, STATES
from core.data_loader import availability, get_timeseries
import core.hotspots as hotspot_data
from core.hotspots import get_hotspots
from core.interpret import build_event_response, build_trend_response
from core.stats import seasonal_trend
from data_pipeline.build_dataset import PRECIPITATION_COLUMN, TEMPERATURE_COLUMN
from ml.events import model_event_chances
from core.interpret import WORDS as WORDS_VARIABLES

app = Flask(__name__)


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/options")
def options():
    """Drives both dropdowns; has_data tells the UI what is not ready yet."""
    avail = availability()
    return jsonify({
        "states": [{**s, "has_data": s["code"] in avail} for s in STATES],
        "parameters": [
            {**p, "has_data": any(p["key"] in v for v in avail.values())}
            for p in PARAMETERS
        ],
    })


@app.route("/api/hotspots")
def hotspots():
    """Model-predicted hotspots for one state (latest month in data/processed/hotspots.csv)."""
    state_info = next((s for s in STATES if s["code"] == request.args.get("state", "")), None)
    if state_info is None:
        return jsonify({"error": "Unknown state."}), 400
    try:
        df, problems = get_hotspots(state_info["code"])
    except Exception as exc:  # unreadable file: say so instead of crashing the page
        app.logger.error("hotspots.csv could not be read: %s", exc)
        df, problems = None, ["hotspots.csv could not be read"]
    for p in problems:
        app.logger.warning("hotspots.csv: %s", p)
    base = {"state": state_info["name"], "view": state_info["view"], "bbox": state_info.get("bbox"),
            "skipped": len(problems),
            "demo": hotspot_data.USE_DEMO_HOTSPOTS,
            "legend": [{"key": k, "label": v["label"], "color": v["color"]} for k, v in PHENOMENA.items()]}
    if df is None or df.empty:
        msg = (f"No hotspot predictions for {state_info['name']} yet. "
               "They will appear here once the model's output is added.")
        return jsonify({**base, "available": False, "message": msg, "hotspots": []})
    return jsonify({
        **base, "available": True, "message": "",
        "for_month": df["for_month"].iloc[0].strftime("%B %Y"),
        "hotspots": [{
            "lat": r.lat, "lon": r.lon, "phenomenon": r.phenomenon,
            "label": PHENOMENA[r.phenomenon]["label"], "color": PHENOMENA[r.phenomenon]["color"],
            "probability_pct": round(r.probability * 100),
        } for r in df.itertuples()],
    })


_trend_cache = {}


def _trend(state, variable, depth, source, g):
    """Cached trend statistics for one series (source block of the data)."""
    key = (state, variable, depth, source, len(g), str(g["date"].max()))
    if key not in _trend_cache:
        _trend_cache[key] = seasonal_trend(g[["date", "value"]])
    return _trend_cache[key]


@app.route("/api/timeseries")
def timeseries():
    variable = request.args.get("variable", "")
    state = request.args.get("state", "")
    depth = request.args.get("depth") or None
    df = get_timeseries(variable, state, request.args.get("start"),
                        request.args.get("end"), depth)
    param = next((p for p in PARAMETERS if p["key"] == variable), None)
    state_info = next((s for s in STATES if s["code"] == state), None)
    if param is None or state_info is None:
        return jsonify({"error": "Unknown state or measurement."}), 400
    if df.empty:
        return jsonify({
            "available": False,
            "message": f"No {param['label'].lower()} data for {state_info['name']} yet.",
        })

    series = []
    for source, g in df.groupby("source", sort=True):
        rolling = g["value"].rolling(12, min_periods=12).mean()
        series.append({
            "name": source,
            "dates": g["date"].dt.strftime("%Y-%m-%d").tolist(),
            "values": g["value"].round(2).tolist(),
            "rolling12": [None if v != v else round(v, 2) for v in rolling],
            "trend": _trend_line(_trend(state, variable, depth, source, g)),
        })
    return jsonify({
        "available": True,
        "state": state_info["name"],
        "label": param["label"],
        "source": param["source"],
        "note": param.get("note", ""),
        "unit": df["unit"].iloc[0],
        "series": series,
    })


def _trend_line(t):
    """Only what the chart needs to draw the dashed trend line."""
    return None if t is None else {"line": t["line"], "significant": t["significant"]}


@app.route("/api/trend")
def trend():
    variable = request.args.get("variable", "")
    state = request.args.get("state", "")
    depth = request.args.get("depth") or None
    df = get_timeseries(variable, state, depth=depth)
    param = next((p for p in PARAMETERS if p["key"] == variable), None)
    state_info = next((s for s in STATES if s["code"] == state), None)
    if param is None or state_info is None:
        return jsonify({"error": "Unknown state or measurement."}), 400
    if df.empty:
        return jsonify({"available": False,
                        "message": f"No {param['label'].lower()} data for {state_info['name']} yet."})
    results = {}
    for source, g in df.groupby("source", sort=True):
        t = _trend(state, variable, depth, source, g)
        if t is not None:
            results[source] = t
    if not results:
        return jsonify({"available": False, "message": "There isn't enough data yet to test for a trend."})
    return jsonify(build_trend_response(results, variable, state_info["name"]))


_event_cache = {}
_model_event_data = None


def _load_model_event_data():
    global _model_event_data
    if _model_event_data is None:
        from ml.nasa_model import TEST_PREDICTIONS_PATH, forecast_monthly

        validation = pd.read_csv(TEST_PREDICTIONS_PATH)
        _model_event_data = (forecast_monthly(), validation)
    return _model_event_data


@app.route("/api/event-chance")
def event_chance():
    variable = request.args.get("variable", "")
    state = request.args.get("state", "")
    depth = request.args.get("depth") or None
    df = get_timeseries(variable, state, depth=depth)
    param = next((p for p in PARAMETERS if p["key"] == variable), None)
    state_info = next((s for s in STATES if s["code"] == state), None)
    if param is None or state_info is None:
        return jsonify({"error": "Unknown state or measurement."}), 400
    if df.empty:
        return jsonify({"available": False,
                        "message": f"No {param['label'].lower()} data for {state_info['name']} yet."})
    if variable not in WORDS_VARIABLES:
        return jsonify({"available": False,
                        "message": f"Event chance estimates are not available for {param['label'].lower()}."})

    source, source_depth = (
        df.groupby(["source", "depth"], dropna=False).size().idxmax()
    )
    sub = df[
        (df["source"] == source) & (df["depth"] == source_depth)
    ][["date", "value"]]
    factor = (
        f"{source}_{source_depth}"
        if variable == "soil_moisture"
        else {
            "temperature": TEMPERATURE_COLUMN,
            "precipitation": PRECIPITATION_COLUMN,
        }[variable]
    )
    key = (state, variable, source, source_depth, len(sub), str(sub["date"].max()))
    if key not in _event_cache:
        forecasts, validation = _load_model_event_data()
        state_name = state_info["name"]
        model_forecasts = forecasts[
            (forecasts["state"] == state_name)
            & (forecasts["factor"] == factor)
        ]
        current_month = pd.Timestamp.today().to_period("M").to_timestamp()
        model_forecasts = model_forecasts[
            pd.to_datetime(model_forecasts["date"]) >= current_month
        ].sort_values("date")
        if model_forecasts.empty:
            return jsonify({
                "available": False,
                "message": "The NASA model has no forecast for the current or a future month. "
                           "Refresh the cleaned data and rebuild the model forecasts.",
            })
        forecast = model_forecasts.iloc[0]
        validation_rows = validation[
            (validation["state"] == state_name)
            & (validation["factor"] == factor)
        ]
        errors = (
            pd.to_numeric(validation_rows["actual"], errors="coerce")
            - pd.to_numeric(validation_rows["predicted"], errors="coerce")
        )
        _event_cache[key] = model_event_chances(
            sub,
            forecast["predicted_value"],
            forecast["date"],
            errors,
            scale=100 if variable == "soil_moisture" else 1,
        )
    result = _event_cache[key]
    if result is None:
        return jsonify({"available": False,
                        "message": "There isn't enough history or held-out model data to estimate this yet."})
    return jsonify(build_event_response(result, variable, state_info["name"], source))


if __name__ == "__main__":
    app.run(debug=True)
