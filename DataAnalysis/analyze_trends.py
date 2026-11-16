#!/usr/bin/env python3
"""
Step 1 of the pipeline: find the trend of every factor in every state.

Setup: save as DataAnalysis/analyze_trends.py and run clean_nasa_data.py first (it creates Cleaned/).
       needs: pip install pandas numpy matplotlib
Usage: from inside DataAnalysis, run
    python analyze_trends.py
Options: [root_folder] [--min-years 15]

Reads   Cleaned/<State>/<State>_clean.csv   (every data column is a "factor")
Writes  Cleaned/Trends/
    trend_table.csv       one row per state x factor x period (annual, DJF, MAM, JJA, SON):
                          slope per decade, percent per decade, years used
    trend_components.csv  every month of every factor split into value = trend + seasonal + residual
                          (this is the time series the unified dataset and the model will use)
    annual_values.csv     the yearly numbers behind the plots
    figures/<factor>.png  one figure per factor, one panel per state

Method
  * Rate of change: Theil-Sen slope (median of all pairwise slopes, robust to outliers) per decade, on annual
    values from COMPLETE calendar years only. Seasonal trends use complete seasons (Dec belongs to the next year's DJF).
    Precipitation is summed, everything else is averaged.
  * Monthly trend series: trend_linear = the Theil-Sen line evaluated at each month;
    trend_smooth = centred 2x12-month moving average (follows multi-year swings; empty for the first and last 6 months);
    seasonal = average calendar-month pattern left after removing trend_smooth; residual = what is left over.
  * Significance is NOT computed here. That is the next script.
"""
import argparse
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COLORS = {"Texas": "#D55E00", "Alabama": "#0072B2", "New York": "#009E73"}   # colour-blind safe
OTHER = "#CC79A7"
SEASONS = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
           6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"}
PERIODS = ["annual", "DJF", "MAM", "JJA", "SON"]
FAMILY = {"soil": "soil_moisture", "precip": "precipitation", "temp": "temperature", "other": "other"}


def pretty_state(folder):
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", folder)


def kind_unit(name):
    n = name.lower()
    if n.startswith(("fldas", "nldas", "gldas")):
        return "soil", "m³/m³"
    if n.startswith("precip"):
        return "precip", "mm/yr"
    if re.search(r"t2m|tsurf|temp|tmax|tmin|dew|wet", n):
        return "temp", "°C"
    return "other", ""


def annual(series, how):
    """Complete calendar years only (12 months present)."""
    g = series.groupby(series.index.year)
    vals = g.sum() if how == "sum" else g.mean()
    return vals[g.count() == 12]


def seasonal(series, season, how):
    """Complete seasons only (3 months present); December counts toward the next year's DJF."""
    sel = series[[SEASONS[m] == season for m in series.index.month]]
    g = sel.groupby(sel.index.year + (sel.index.month == 12))
    vals = g.sum() if how == "sum" else g.mean()
    return vals[g.count() == 3]


def sen(x, y):
    """Theil-Sen slope and intercept."""
    i, j = np.triu_indices(len(x), 1)
    b = np.median((y[j] - y[i]) / (x[j] - x[i]))
    return b, np.median(y - b * x)


def decompose(s, b, c, scale):
    """value = trend_smooth + seasonal + residual, plus the linear trend line, all monthly."""
    s = s.asfreq("MS")
    smooth = s.rolling(13, center=True).apply(lambda w: (w[0] / 2 + w[1:-1].sum() + w[-1] / 2) / 12, raw=True)
    seas = (s - smooth).groupby(s.index.month).transform("mean")
    t = s.index.year + (s.index.month - 6.5) / 12          # same axis as the annual values (mid-year = year)
    return pd.DataFrame({"value": s, "trend_linear": (c + b * t) * scale, "trend_smooth": smooth,
                         "seasonal": seas, "residual": s - smooth - seas})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", help="folder containing Cleaned/ (default: this script's folder)")
    ap.add_argument("--min-years", type=int, default=15, help="minimum complete years for an annual trend (default 15)")
    a = ap.parse_args()

    root = Path(a.root).resolve() if a.root else Path(__file__).resolve().parent
    files = sorted((root / "Cleaned").glob("*/*_clean.csv"))
    if not files:
        sys.exit(f"No Cleaned/<State>/<State>_clean.csv files in {root}. Run clean_nasa_data.py first.")
    out = root / "Cleaned" / "Trends"
    (out / "figures").mkdir(parents=True, exist_ok=True)

    rows, yearly, comps, lines = [], [], [], {}
    for f in files:
        state = pretty_state(f.parent.name)
        df = pd.read_csv(f, index_col=0, parse_dates=True).select_dtypes("number")
        for col in df.columns:
            kind, unit = kind_unit(col)
            how = "sum" if kind == "precip" else "mean"
            for period in PERIODS:
                ser = annual(df[col], how) if period == "annual" else seasonal(df[col], period, how)
                ser = ser.dropna()
                need = a.min_years if period == "annual" else a.min_years
                if len(ser) < need:
                    if period == "annual":
                        print(f"  skipped {state} / {col}: only {len(ser)} complete years")
                    continue
                x, y = ser.index.values.astype(float), ser.values
                b, c = sen(x, y)
                mean = y.mean()
                u = "mm/season" if (kind == "precip" and period != "annual") else unit
                rows.append(dict(variable=FAMILY[kind], factor=col, state=state, period=period, unit=u,
                                 first_year=int(x[0]), last_year=int(x[-1]), n_years=len(y), mean=mean,
                                 slope_per_decade=b * 10,
                                 pct_per_decade=(b * 10 / mean * 100) if kind in ("soil", "precip") and mean else np.nan,
                                 direction="up" if b > 0 else "down" if b < 0 else "flat"))
                if period == "annual":
                    lines[(state, col)] = (b, c)
                    yearly += [dict(state=state, factor=col, year=int(k), value=v) for k, v in ser.items()]
                    d = decompose(df[col], b, c, 1 / 12 if kind == "precip" else 1)
                    d.insert(0, "factor", col)
                    d.insert(0, "state", state)
                    d.insert(0, "variable", FAMILY[kind])
                    comps.append(d.rename_axis("date").reset_index())

    t = pd.DataFrame(rows)
    t.sort_values(["variable", "factor", "state", "period"]).to_csv(out / "trend_table.csv", index=False, float_format="%.6g")
    pd.concat(comps).to_csv(out / "trend_components.csv", index=False, float_format="%.6g")
    yv = pd.DataFrame(yearly)
    yv.to_csv(out / "annual_values.csv", index=False, float_format="%.6g")

    ann = t[t.period == "annual"]
    for factor, g in ann.groupby("factor"):
        states = sorted(g["state"])
        fig, axes = plt.subplots(len(states), 1, figsize=(8, 2.7 * len(states) + 0.6), sharex=True, squeeze=False)
        for ax, st in zip(axes[:, 0], states):
            r = g[g.state == st].iloc[0]
            yr = yv[(yv.state == st) & (yv.factor == factor)]
            b, c = lines[(st, factor)]
            col = COLORS.get(st, OTHER)
            ax.plot(yr.year, yr.value, "-o", ms=3.5, lw=1.4, color=col)
            xs = np.array([r.first_year, r.last_year], float)
            ax.plot(xs, c + b * xs, "--", color="black", lw=1.6)
            pct = f" ({r.pct_per_decade:+.1f}% of mean)" if not np.isnan(r.pct_per_decade) else ""
            ax.set_title(f"{st}: {r.slope_per_decade:+.4g} {r.unit} per decade{pct}", loc="left", fontsize=9.5)
            ax.set_ylabel(r.unit, fontsize=9)
            ax.grid(alpha=0.25)
            ax.spines[["top", "right"]].set_visible(False)
        label = "Precipitation (annual total)" if kind_unit(factor)[0] == "precip" else factor.replace("_", " ")
        fig.suptitle(f"{label}: annual values and Theil-Sen trend", fontsize=11.5)
        axes[-1, 0].set_xlabel("Year (complete calendar years only)", fontsize=9)
        fig.tight_layout()
        fig.savefig(out / "figures" / f"{factor}.png", dpi=150)
        plt.close(fig)

    show = ann[["state", "factor", "first_year", "last_year", "slope_per_decade", "pct_per_decade", "direction"]]
    print(show.sort_values(["factor", "state"]).to_string(index=False, float_format=lambda v: f"{v:.4g}"))
    print(f"\n{len(t)} trends ({t.factor.nunique()} factors x {t.state.nunique()} states x {len(PERIODS)} periods), "
          f"monthly components and {ann.factor.nunique()} figures written to {out}/")


if __name__ == "__main__":
    main()
