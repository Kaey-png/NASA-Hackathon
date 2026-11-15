"""Checks that the trend test recovers trends we plant ourselves (not app data).
Run from the project root:  python -m tests.test_stats
"""
import numpy as np
import pandas as pd

from core.stats import seasonal_trend


def make_series(start, months, slope_per_year, seasonal_amp=5.0, noise=1.5, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, periods=months, freq="MS")
    t = np.arange(months) / 12.0
    season = seasonal_amp * np.sin(2 * np.pi * (dates.month - 1) / 12)
    return pd.DataFrame({"date": dates,
                         "value": 30 + slope_per_year * t + season + rng.normal(0, noise, months)})


def test_recovers_planted_slope():
    for true in (0.05, -0.08):
        r = seasonal_trend(make_series("1982-09-01", 529, true))
        assert abs(r["slope_per_year"] - true) < 0.015, (true, r["slope_per_year"])
        assert r["significant"], true
        lo, hi = r["ci_per_year"]
        assert lo <= true <= hi, (true, lo, hi)


def test_flat_series_is_not_significant():
    false_alarms = sum(seasonal_trend(make_series("1982-09-01", 529, 0.0, seed=s))["significant"]
                       for s in range(40))
    assert false_alarms <= 6, f"{false_alarms}/40 false alarms (expect about 2)"


def test_partial_years_and_strong_season_do_not_fake_a_trend():
    # Starts in June, ends in September, huge seasonal swing, no trend.
    false_alarms = sum(seasonal_trend(make_series("2000-06-01", 304, 0.0, seasonal_amp=40, seed=s))["significant"]
                       for s in range(40))
    assert false_alarms <= 6, f"{false_alarms}/40 false alarms"


def test_short_noisy_record_is_usually_not_significant():
    r = seasonal_trend(make_series("2019-01-01", 93, 0.02, noise=3.0))
    assert r is not None and not r["significant"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok  ", name)
