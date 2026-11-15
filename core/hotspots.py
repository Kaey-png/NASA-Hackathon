"""Reads the model's hotspot file (data/processed/hotspots.csv) and validates it.

Columns: state, lat, lon, phenomenon, probability, for_month
Bad rows are skipped (and reported) so one typo never blanks the whole map.
"""
import pandas as pd

from config import DEMO_HOTSPOTS_PATH, HOTSPOTS_PATH, PHENOMENA, STATES, USE_DEMO_HOTSPOTS

REQUIRED = ["state", "lat", "lon", "phenomenon", "probability", "for_month"]
STATE_INFO = {s["code"]: s for s in STATES}


def load_hotspots():
    """Returns (valid_rows_dataframe, list_of_problem_strings)."""
    empty = pd.DataFrame(columns=REQUIRED)
    path = DEMO_HOTSPOTS_PATH if USE_DEMO_HOTSPOTS else HOTSPOTS_PATH
    if not path.exists():
        return empty, []
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if df.empty:
        return empty, []
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        return empty, [f"hotspots.csv is missing columns: {missing}"]

    problems, keep = [], []
    for idx, row in df.iterrows():
        line = idx + 2  # +1 for header, +1 for 1-based
        state = row["state"].strip().upper()
        pheno = row["phenomenon"].strip().lower()
        try:
            lat, lon = float(row["lat"]), float(row["lon"])
            prob = float(row["probability"])
            month = pd.to_datetime(row["for_month"]).to_period("M").to_timestamp()
        except (ValueError, TypeError):
            problems.append(f"row {line}: a lat, lon, probability or for_month value could not be read")
            continue
        if state not in STATE_INFO:
            problems.append(f"row {line}: unknown state '{row['state']}'")
        elif pheno not in PHENOMENA:
            problems.append(f"row {line}: unknown phenomenon '{row['phenomenon']}' (use {list(PHENOMENA)})")
        elif not 0 <= prob <= 1:
            problems.append(f"row {line}: probability {prob} must be between 0 and 1 (not a percentage)")
        else:
            s, w, n, e = STATE_INFO[state]["bbox"]
            if not (s - 0.1 <= lat <= n + 0.1 and w - 0.1 <= lon <= e + 0.1):
                problems.append(f"row {line}: ({lat}, {lon}) is outside {STATE_INFO[state]['name']} "
                                "(are lat and lon swapped?)")
            else:
                keep.append({"state": state, "lat": lat, "lon": lon, "phenomenon": pheno,
                             "probability": prob, "for_month": month})
    return (pd.DataFrame(keep, columns=REQUIRED) if keep else empty), problems


def get_hotspots(state):
    """Hotspots for one state, for the latest month in the file. Returns (df, problems)."""
    df, problems = load_hotspots()
    df = df[df["state"] == state]
    if not df.empty:
        df = df[df["for_month"] == df["for_month"].max()]
    return df.sort_values("probability", ascending=False).reset_index(drop=True), problems
