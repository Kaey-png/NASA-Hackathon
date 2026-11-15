import tempfile
from pathlib import Path

import pandas as pd

from data_pipeline.build_dataset import (
    PRECIPITATION_COLUMN,
    SOIL_COLUMNS,
    TEMPERATURE_COLUMN,
    build_dataset,
)


def _write_cleaned_files(root):
    for folder in ("Alabama", "Texas", "NewYork"):
        state_dir = root / folder
        state_dir.mkdir(parents=True)
        data = {
            "date": ["2020-01-01", "2020-02-01"],
            TEMPERATURE_COLUMN: [15.25, 16.75],
            PRECIPITATION_COLUMN: [100.25, None],
        }
        data.update({column: [0.2, 0.3] for column in SOIL_COLUMNS})
        pd.DataFrame(data).to_csv(state_dir / f"{folder}_clean.csv", index=False)


def test_build_dataset_uses_cleaned_measurements_and_units():
    with tempfile.TemporaryDirectory() as temporary_dir:
        cleaned_dir = Path(temporary_dir)
        _write_cleaned_files(cleaned_dir)

        result = build_dataset(cleaned_dir)

    assert set(result["state"]) == {"AL", "TX", "NY"}
    assert set(result["variable"]) == {"temperature", "precipitation", "soil_moisture"}

    temperature = result[result["variable"] == "temperature"]
    assert len(temperature) == 6
    assert set(temperature["unit"]) == {"°C"}
    assert set(temperature["source"]) == {"MERRA-2"}
    assert set(temperature["value"]) == {15.25, 16.75}

    precipitation = result[result["variable"] == "precipitation"]
    assert len(precipitation) == 3
    assert set(precipitation["value"]) == {100.25}
    assert set(precipitation["unit"]) == {"mm/month"}

    soil = result[result["variable"] == "soil_moisture"]
    assert len(soil) == 48
    assert set(soil["value"]) == {20.0, 30.0}
    assert set(soil["unit"]) == {"% of soil volume"}
    assert set(soil["source"]) == {"FLDAS", "NLDAS"}
    assert set(soil["depth"]) == {
        "0-10cm", "10-40cm", "40-100cm", "100-200cm",
    }


if __name__ == "__main__":
    test_build_dataset_uses_cleaned_measurements_and_units()
