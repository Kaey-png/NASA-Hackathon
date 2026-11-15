"""Checks hotspot-file validation. Uses a temporary made-up file, never the real data.
Run from the project root:  python -m tests.test_hotspots
"""
import tempfile
from pathlib import Path

import core.hotspots as hs

ROWS = """state,lat,lon,phenomenon,probability,for_month
TX,31.2,-99.4,drought,0.58,2026-10
TX,31.9,-100.1,drought,0.31,2026-10
TX,29.7,-95.4,flood,0.12,2026-09
TX,-99.4,31.2,drought,0.5,2026-10
TX,31.0,-99.0,drought,58,2026-10
TX,31.0,-99.0,tornado,0.4,2026-10
ZZ,31.0,-99.0,drought,0.4,2026-10
TX,abc,-99.0,drought,0.4,2026-10
AL,32.6,-86.9,flood,0.12,2026-10
"""


hs.USE_DEMO_HOTSPOTS = False  # tests point at their own temporary file


def with_file(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False)
    f.write(text); f.close()
    hs.HOTSPOTS_PATH = Path(f.name)


def test_valid_rows_kept_bad_rows_reported():
    with_file(ROWS)
    df, problems = hs.load_hotspots()
    assert len(df) == 4, len(df)          # 3 TX + 1 AL valid
    assert len(problems) == 5, problems   # swapped, percent, tornado, ZZ, abc
    assert any("swapped" in p for p in problems)
    assert any("not a percentage" in p for p in problems)


def test_latest_month_only_and_sorted():
    with_file(ROWS)
    df, _ = hs.get_hotspots("TX")
    assert list(df["probability"]) == [0.58, 0.31]      # the 2026-09 flood row is older
    assert df["for_month"].nunique() == 1


def test_header_only_and_missing_file_are_empty():
    with_file("state,lat,lon,phenomenon,probability,for_month\n")
    assert hs.load_hotspots()[0].empty
    hs.HOTSPOTS_PATH = Path("/nonexistent/hotspots.csv")
    df, problems = hs.load_hotspots()
    assert df.empty and problems == []


def test_missing_column_is_reported():
    with_file("state,lat,lon\nTX,31,-99\n")
    df, problems = hs.load_hotspots()
    assert df.empty and "missing columns" in problems[0]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok  ", name)
