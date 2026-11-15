"""All data access goes through this file. The rest of the app never reads CSVs."""
import pandas as pd

from config import DATA_PATH, PARAMETERS, STATES

REQUIRED = ["date", "state", "variable", "value", "unit"]
OPTIONAL = ["source", "depth"]  # filled with "" when a file has no such column
VALID_STATES = {s["code"] for s in STATES}
VALID_VARIABLES = {p["key"] for p in PARAMETERS}


def load_all():
    """Read and validate the processed CSV. Raises ValueError if it breaks the contract."""
    if not DATA_PATH.exists():
        return pd.DataFrame(columns=REQUIRED + OPTIONAL)
    df = pd.read_csv(DATA_PATH, parse_dates=["date"], keep_default_na=False,
                     na_values=[], dtype={"source": str, "depth": str})
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"monthly.csv is missing columns: {missing}")
    for col in OPTIONAL:
        if col not in df.columns:
            df[col] = ""
    bad_state = set(df["state"]) - VALID_STATES
    bad_var = set(df["variable"]) - VALID_VARIABLES
    if bad_state or bad_var:
        raise ValueError(f"Unknown states {bad_state} or variables {bad_var}")
    return df


def availability():
    """{'AL': ['soil_moisture'], ...} for every state that has data."""
    df = load_all()
    return {s: sorted(g["variable"].unique()) for s, g in df.groupby("state")}


def get_timeseries(variable, state, start=None, end=None, depth=None):
    """Monthly rows for one state and variable (one block per source).
    Empty DataFrame if there is no data."""
    df = load_all()
    df = df[(df["variable"] == variable) & (df["state"] == state)]
    if depth:
        df = df[df["depth"] == depth]
    if start:
        df = df[df["date"] >= pd.Timestamp(start)]
    if end:
        df = df[df["date"] <= pd.Timestamp(end)]
    return df.sort_values(["source", "date"]).reset_index(drop=True)
