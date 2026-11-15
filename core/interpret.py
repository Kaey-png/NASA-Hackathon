"""Turns model numbers into plain-English text for non-technical users."""
from datetime import date

WORDS = {
    "temperature": {
        "subject": "air temperature",
        "low": {"label": "Unusually cool month", "hazard": "cold conditions",
                "phrase": "much cooler than usual"},
        "high": {"label": "Unusually hot month", "hazard": "heat risk",
                 "phrase": "much warmer than usual"},
    },
    "soil_moisture": {
        "subject": "soil moisture",
        "low": {"label": "Very dry soil", "hazard": "drought risk",
                "phrase": "much drier than usual"},
        "high": {"label": "Very wet soil", "hazard": "flood risk",
                 "phrase": "much wetter than usual"},
    },
    "precipitation": {
        "subject": "rainfall",
        "low": {"label": "Very dry month", "hazard": "drought risk",
                "phrase": "much drier than usual"},
        "high": {"label": "Very wet month", "hazard": "flood risk",
                 "phrase": "much wetter than usual"},
    },
}
CURRENT = {
    -1: "below its usual range",
    0: "within its usual range",
    1: "above its usual range",
}


def _month(ts):
    return ts.strftime("%B %Y")


def _skill_text(skill):
    if skill is None:
        return ""
    if skill > 0.02:
        return f"In a test on past years, this beat simply guessing the usual rate by {round(skill * 100)}%."
    if skill >= -0.02:
        return "In a test on past years, this was about as good as simply guessing the usual rate."
    return "In a test on past years, this did not beat simply guessing the usual rate, so treat it with caution."


def build_event_response(result, variable, state_name, source):
    words = WORDS[variable]
    events = []
    for e in sorted(result["events"], key=lambda e: e["probability"], reverse=True):
        w = words[e["key"]]
        pct, normal = round(e["probability"] * 100), round(e["normal_rate"] * 100)
        ratio = e["probability"] / e["normal_rate"] if e["normal_rate"] else 1
        trend = "higher" if ratio >= 1.25 else "lower" if ratio <= 0.75 else "usual"
        events.append({
            "key": e["key"], "label": w["label"], "hazard": w["hazard"],
            "probability_pct": pct, "normal_pct": normal, "trend": trend,
            "sentence": (f"The chance that {state_name}'s {words['subject']} will be "
                         f"{w['phrase']} in {_month(result['for_month'])} is about {pct}%. "
                         f"That usually happens in about {normal}% of months."),
            "skill_text": _skill_text(e["skill"]),
            "low_confidence": e["low_confidence"],
        })

    years = round(result["history_months"] / 12)
    basis = (
        f"Based on {years} years of {source + ' ' if source else ''}data through "
        f"{_month(result['as_of'])}. The estimate uses the model forecast and held-out "
        f"model errors. Latest reading: {CURRENT[result['current']]}. "
        f"Method: {result['model']}."
    )

    today = date.today()
    behind = (today.year - result["for_month"].year) * 12 + today.month - result["for_month"].month
    note = ""
    if behind > 2:
        note = (f"The latest data is from {_month(result['as_of'])}, so this estimate is for a "
                "month that has already passed.")
    return {"available": True, "events": events, "basis": basis, "note": note,
            "for_month": _month(result["for_month"])}


# ---------- trend verdict ----------
SUBJECT = {
    "soil_moisture": "soil moisture",
    "precipitation": "rainfall",
    "temperature": "air temperature",
}


def _num(v):
    v = abs(v)
    return f"{v:.0f}" if v >= 10 else f"{v:.1f}" if v >= 1 else f"{v:.2f}"


def _amount(variable, v):
    if variable == "soil_moisture":
        return f"{_num(v)} percentage points"
    if variable == "temperature":
        return f"{_num(v)} °C"
    return f"{_num(v)} mm per month"


def _signed(v):
    return f"{v:+.2f}"


def build_trend_response(results, variable, state_name):
    """results: {source_name: seasonal_trend() dict}. Source name '' means a single unnamed source."""
    subject = SUBJECT[variable]
    named = all(results.keys())
    unit_short = {
        "soil_moisture": "points",
        "precipitation": "mm/month",
        "temperature": "°C",
    }[variable]
    is_temperature = variable == "temperature"
    out = []
    for name, r in results.items():
        increasing = r["direction"] == "up"
        word = ("warmer" if increasing else "cooler") if is_temperature else (
            "wetter" if increasing else "drier"
        )
        change = ("warming" if increasing else "cooling") if is_temperature else word
        per_decade, total = r["slope_per_year"] * 10, r["total_change"]
        if r["significant"]:
            sentence = (f"{state_name}'s {subject} is {change}, by about {_amount(variable, per_decade)} "
                        f"per decade ({_amount(variable, total)} in total since {r['start_year']}). "
                        "This change is statistically significant: it is very unlikely to be just normal ups and downs.")
            badge, kind = ("Significant increase", "up") if increasing else ("Significant decrease", "down")
            if is_temperature:
                badge = "Significant warming" if increasing else "Significant cooling"
        else:
            trend_word = "warmer" if is_temperature and increasing else (
                "cooler" if is_temperature else word
            )
            sentence = (f"No clear trend in {state_name}'s {subject}. It has tilted slightly {trend_word} "
                        f"(about {_amount(variable, per_decade)} per decade), but that is small compared with its "
                        "normal ups and downs, so we can't call it a real change.")
            badge, kind = "No significant trend", "none"
        note = ""
        if r["years"] < 10:
            note = f"This record covers only {_num(r['years'])} years, which is short for judging trends."
        p = r["p_value"]
        lo, hi = (v * 10 for v in r["ci_per_year"])
        out.append({
            "name": name, "label": f"{name} model" if named else "",
            "badge": badge, "kind": kind, "sentence": sentence, "note": note,
            "details": {
                "slope": f"{_signed(per_decade)} {unit_short} per decade",
                "range": f"{_signed(lo)} to {_signed(hi)} {unit_short} per decade",
                "p_value": "less than 0.001" if p < 0.001 else f"{p:.3f}",
                "years": f"{r['start_year']}\u2013{r['end_year']} ({_num(r['years'])} years)",
            },
        })

    agreement = ""
    if len(out) > 1:
        kinds = {o["kind"] for o in out}
        if kinds == {"none"}:
            agreement = "Neither model shows a clear trend."
        elif len(kinds) == 1:
            agreement = "Both models agree on this trend."
        else:
            agreement = "The two models disagree, so treat this trend with caution."
    method = ("Method: seasonal Mann-Kendall test with Sen's slope. Each calendar month is compared only with "
              "the same month in other years, so the yearly cycle can't create a fake trend. "
              "\u201cSignificant\u201d means the p-value is below 0.05.")
    return {"available": True, "results": out, "agreement": agreement, "method": method}
