"""Build app measurements from the cleaned monthly state datasets."""
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
CLEANED_DIR = BASE_DIR / "data" / "cleaned"
OUT = BASE_DIR / "data" / "processed" / "monthly.csv"

STATE_FILES = {"Alabama": "AL", "Texas": "TX", "NewYork": "NY"}
TEMPERATURE_COLUMN = "M2TMNXSLV_5_12_4_T2M"
PRECIPITATION_COLUMN = "precip_mm_month"
SOIL_COLUMNS = (
    "FLDAS_0-10cm",
    "FLDAS_10-40cm",
    "FLDAS_40-100cm",
    "FLDAS_100-200cm",
    "NLDAS_0-10cm",
    "NLDAS_10-40cm",
    "NLDAS_40-100cm",
    "NLDAS_100-200cm",
)


def _records(data, state, variable, column, unit, source="", depth="", scale=1):
    values = pd.to_numeric(data[column], errors="coerce")
    valid = data["date"].notna() & values.notna()
    if not valid.any():
        return pd.DataFrame()
    return pd.DataFrame({
        "date": data.loc[valid, "date"].to_numpy(),
        "state": state,
        "variable": variable,
        "value": (values.loc[valid] * scale).round(2).to_numpy(),
        "unit": unit,
        "source": source,
        "depth": depth,
    })


def build_dataset(cleaned_dir=CLEANED_DIR):
    frames = []
    for folder, state in STATE_FILES.items():
        path = Path(cleaned_dir) / folder / f"{folder}_clean.csv"
        if not path.exists():
            raise FileNotFoundError(f"Cleaned state data not found: {path}")

        data = pd.read_csv(path)
        required = ["date", TEMPERATURE_COLUMN, PRECIPITATION_COLUMN, *SOIL_COLUMNS]
        missing = [column for column in required if column not in data.columns]
        if missing:
            raise ValueError(f"{path} is missing required columns: {missing}")
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        if data["date"].isna().any():
            raise ValueError(f"{path} contains invalid monthly dates")
        if data["date"].duplicated().any():
            raise ValueError(f"{path} contains duplicate monthly dates")

        frames.append(_records(
            data, state, "temperature", TEMPERATURE_COLUMN, "°C", "MERRA-2"
        ))
        frames.append(_records(
            data, state, "precipitation", PRECIPITATION_COLUMN,
            "mm/month", "GPM IMERG"
        ))
        for column in SOIL_COLUMNS:
            source, depth = column.split("_", maxsplit=1)
            frames.append(_records(
                data, state, "soil_moisture", column,
                "% of soil volume", source, depth, scale=100
            ))

    columns = ["date", "state", "variable", "value", "unit", "source", "depth"]
    return (
        pd.concat(frames, ignore_index=True)
        .sort_values(["state", "variable", "depth", "source", "date"])
        .reset_index(drop=True)[columns]
    )


def build():
    out = build_dataset()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False, date_format="%Y-%m-%d")
    print(f"Wrote {len(out)} rows to {OUT}")
    return out


if __name__ == "__main__":
    build()
