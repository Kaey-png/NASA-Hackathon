#!/usr/bin/env python3
"""
NASA Hackathon: Significance and Environmental Importance Analysis

Run after clean_nasa_data.py and analyze_trends.py:

    python analyze_significance.py

Expected input:
    Cleaned/<State>/<State>_clean.csv

Outputs:
    Cleaned/Significance/significance_table.csv
    Cleaned/Significance/environmental_importance_indicators.csv
    Cleaned/Significance/five_year_trend_continuation.csv
    Cleaned/Significance/figures/
    Cleaned/Significance/figures/individual_time_series/

Statistical significance does not equal environmental importance
and does not establish causation.

Future values are trend-continuation scenarios, not forecasts.
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

from scipy.stats import norm, theilslopes, kendalltau
from statsmodels.tsa.stattools import acf
from statsmodels.stats.multitest import multipletests


SEASONS = {
    12: "DJF", 1: "DJF", 2: "DJF",
    3: "MAM", 4: "MAM", 5: "MAM",
    6: "JJA", 7: "JJA", 8: "JJA",
    9: "SON", 10: "SON", 11: "SON",
}

PERIODS = ["annual", "DJF", "MAM", "JJA", "SON"]


def state_name(folder):
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", folder)


def factor_family(name):
    n = name.lower()

    if n.startswith(("fldas", "nldas", "gldas")):
        return "soil_moisture"

    if n.startswith("precip"):
        return "precipitation"

    if n.endswith("_ts") or any(
        k in n for k in (
            "t2m", "ts_", "dew", "wet",
            "dtr", "temp", "tmax", "tmin"
        )
    ):
        return "temperature"

    return "other"


def aggregate_period(series, period, how):
    """
    Aggregate monthly observations into complete annual
    or seasonal observations.
    """

    s = series.dropna().copy()

    if period == "annual":
        grouped = s.groupby(s.index.year)

        values = (
            grouped.sum()
            if how == "sum"
            else grouped.mean()
        )

        return values[grouped.count() == 12]

    selected = s[
        [SEASONS[m] == period for m in s.index.month]
    ]

    season_year = (
        selected.index.year
        + (selected.index.month == 12)
    )

    grouped = selected.groupby(season_year)

    values = (
        grouped.sum()
        if how == "sum"
        else grouped.mean()
    )

    return values[grouped.count() == 3]


def hamed_rao_mk(y):
    """
    Hamed-Rao modified Mann-Kendall test.

    Adjusts the variance of the Mann-Kendall statistic
    to account for serial autocorrelation.
    """

    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]

    n = len(y)

    if n < 8:
        return np.nan, np.nan, np.nan, 1.0

    s_stat = 0

    for k in range(n - 1):
        s_stat += np.sign(y[k + 1:] - y[k]).sum()

    _, tie_counts = np.unique(
        y,
        return_counts=True
    )

    tie_term = np.sum(
        tie_counts
        * (tie_counts - 1)
        * (2 * tie_counts + 5)
    )

    var_s = (
        n * (n - 1) * (2 * n + 5) - tie_term
    ) / 18.0

    if var_s <= 0:
        return 0.0, 0.0, 1.0, 1.0

    x = np.arange(n, dtype=float)

    slope = theilslopes(y, x).slope

    detrended = y - slope * x

    ranks = pd.Series(
        detrended
    ).rank(method="average").to_numpy()

    max_lag = min(
        n - 1,
        max(1, n // 3)
    )

    acfs = acf(
        ranks,
        nlags=max_lag,
        fft=False,
        adjusted=False
    )

    critical = norm.ppf(0.975) / np.sqrt(n)

    correction_sum = 0.0

    for lag in range(1, max_lag + 1):

        if abs(acfs[lag]) > critical:

            weight = (
                (n - lag)
                * (n - lag - 1)
                * (n - lag - 2)
            )

            if weight > 0:
                correction_sum += weight * acfs[lag]

    cf = 1.0 + (
        2.0
        / (n * (n - 1) * (n - 2))
    ) * correction_sum

    cf = float(
        np.clip(max(1.0, cf), 1.0, 10.0)
    )

    var_s *= cf

    if s_stat > 0:
        z = (s_stat - 1) / np.sqrt(var_s)

    elif s_stat < 0:
        z = (s_stat + 1) / np.sqrt(var_s)

    else:
        z = 0.0

    p = 2.0 * norm.sf(abs(z))

    tau = float(
        kendalltau(
            x,
            y,
            nan_policy="omit"
        ).statistic
    )

    return tau, float(z), float(p), cf


def source_depth(factor):
    m = re.match(
        r"(FLDAS|NLDAS)_(.+)",
        factor,
        flags=re.I
    )

    if not m:
        return None, None

    return m.group(1).upper(), m.group(2)


def add_robustness(table):
    """
    Compare FLDAS and NLDAS measurements
    at matching soil depths.
    """

    table["model_agreement"] = "not_paired"
    table["robust_cross_model"] = False

    paired = {}

    for idx, row in table.iterrows():

        source, depth = source_depth(row.factor)

        if source:
            paired[
                (row.state, depth, row.period, source)
            ] = idx

    for key in list(paired):

        state, depth, period, source = key

        other = (
            "NLDAS"
            if source == "FLDAS"
            else "FLDAS"
        )

        other_idx = paired.get(
            (state, depth, period, other)
        )

        if other_idx is None:
            continue

        i = paired[key]

        a = table.loc[i]
        b = table.loc[other_idx]

        same_direction = (
            a.direction == b.direction
        )

        both_sig = (
            bool(a.significant_fdr)
            and bool(b.significant_fdr)
        )

        agreement = (
            "agree"
            if same_direction
            else "disagree"
        )

        table.loc[i, "model_agreement"] = agreement
        table.loc[other_idx, "model_agreement"] = agreement

        robust = same_direction and both_sig

        table.loc[i, "robust_cross_model"] = robust
        table.loc[other_idx, "robust_cross_model"] = robust

    return table


def plot_heatmap(table, period, output):

    d = table[
        table.period == period
    ].copy()

    if d.empty:
        return

    d["row_label"] = d["factor"].str.replace(
        "_",
        " ",
        regex=False
    )

    pivot = d.pivot_table(
        index="row_label",
        columns="state",
        values="standardized_slope_per_decade",
        aggfunc="first"
    )

    sig = d.pivot_table(
        index="row_label",
        columns="state",
        values="significant_fdr",
        aggfunc="first"
    )

    states = [
        s for s in ["Texas", "Alabama", "New York"]
        if s in pivot.columns
    ]

    pivot = pivot.reindex(columns=states)

    sig = sig.reindex(
        index=pivot.index,
        columns=states
    )

    height = max(
        5.0,
        0.34 * len(pivot) + 1.8
    )

    fig, ax = plt.subplots(
        figsize=(9.0, height)
    )

    values = pivot.to_numpy(dtype=float)

    finite = np.abs(
        values[np.isfinite(values)]
    )

    limit = (
        float(np.nanpercentile(finite, 95))
        if finite.size
        else 1.0
    )

    limit = max(limit, 1e-9)

    im = ax.imshow(
        values,
        aspect="auto",
        cmap="RdBu_r",
        vmin=-limit,
        vmax=limit
    )

    ax.set_xticks(
        range(len(states)),
        states
    )

    ax.set_yticks(
        range(len(pivot)),
        pivot.index,
        fontsize=8
    )

    ax.set_title(
        f"{period.upper()} standardized trend; "
        "* = FDR-significant (q < 0.05)"
    )

    ax.set_xlabel("State")
    ax.set_ylabel("Environmental factor")

    for i, factor in enumerate(pivot.index):

        for j, state in enumerate(states):

            val = pivot.loc[factor, state]

            if pd.notna(val):

                star = (
                    "*"
                    if bool(sig.loc[factor, state])
                    else ""
                )

                ax.text(
                    j,
                    i,
                    f"{val:.3g}{star}",
                    ha="center",
                    va="center",
                    fontsize=7
                )

    cb = fig.colorbar(
        im,
        ax=ax,
        shrink=0.8
    )

    cb.set_label(
        "Theil-Sen slope per decade "
        "(standard deviations)"
    )

    fig.tight_layout()

    fig.savefig(
        output,
        dpi=180,
        bbox_inches="tight"
    )

    plt.close(fig)


def build_annual_series(df, factor):

    family = factor_family(factor)

    how = (
        "sum"
        if family == "precipitation"
        else "mean"
    )

    return aggregate_period(
        df[factor],
        "annual",
        how
    ).dropna()


def trend_continuation(values, horizon=5):
    """
    Estimate a robust linear trend continuation.

    The projection interval is approximate.
    This is not a formal climate forecast.
    """

    x = values.index.to_numpy(dtype=float)
    y = values.to_numpy(dtype=float)

    slope, intercept, low, high = theilslopes(
        y,
        x,
        alpha=0.95
    )

    intercept = float(
        np.median(y - slope * x)
    )

    fitted = intercept + slope * x

    residual_sd = (
        float(np.std(y - fitted, ddof=1))
        if len(y) > 2
        else 0.0
    )

    slope_se = float(
        (high - low) / (2 * 1.96)
    )

    future_years = np.arange(
        int(x.max()) + 1,
        int(x.max()) + horizon + 1
    )

    distance = future_years - x.max()

    pred = (
        intercept + slope * future_years
    )

    spread = 1.96 * np.sqrt(
        residual_sd ** 2
        + (distance * slope_se) ** 2
    )

    return (
        future_years,
        pred,
        pred - spread,
        pred + spread,
        slope,
        low,
        high
    )


def plot_factor_series(
    values,
    row,
    output,
    horizon=5
):

    (
        years,
        pred,
        low,
        high,
        slope,
        slope_low,
        slope_high
    ) = trend_continuation(
        values,
        horizon
    )

    x = values.index.to_numpy(dtype=float)
    y = values.to_numpy(dtype=float)

    fitted = (
        np.median(y - slope * x)
        + slope * x
    )

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        x,
        y,
        marker="o",
        markersize=3,
        linewidth=1.2,
        label="Observed annual values"
    )

    ax.plot(
        x,
        fitted,
        linestyle="--",
        linewidth=1.8,
        label="Historical Theil-Sen trend"
    )

    ax.plot(
        years,
        pred,
        linestyle="--",
        marker="o",
        markersize=3,
        label="5-year trend-continuation scenario"
    )

    ax.fill_between(
        years,
        low,
        high,
        alpha=0.18,
        label="Approx. 95% projection interval"
    )

    ax.axvline(
        x.max() + 0.5,
        color="grey",
        linewidth=1,
        linestyle=":"
    )

    q = row.get(
        "q_value_fdr",
        np.nan
    )

    pval = row.get(
        "p_value",
        np.nan
    )

    sig = (
        "significant (FDR q < 0.05)"
        if bool(row.get("significant_fdr", False))
        else "not significant (FDR q >= 0.05)"
    )

    title = (
        f"{row['state']} — {row['factor']}\n"
        f"Annual trend: {sig}; "
        f"slope={row['slope_per_decade']:.4g}/decade; "
        f"p={pval:.3g}; q={q:.3g}"
    )

    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Year")
    ax.set_ylabel(row.get("unit", "Value"))

    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)

    fig.tight_layout()

    fig.savefig(
        output,
        dpi=160,
        bbox_inches="tight"
    )

    plt.close(fig)

    return years, pred, low, high


def add_importance_indicators(result):

    result[
        "standardized_trend_magnitude"
    ] = result[
        "standardized_slope_per_decade"
    ].abs()

    result[
        "half_period_direction_agreement"
    ] = np.nan

    return result


def main():

    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    ap.add_argument(
        "root",
        nargs="?",
        help="Folder containing Cleaned/ "
             "(default: this script's folder)"
    )

    ap.add_argument(
        "--min-years",
        type=int,
        default=15,
        help="Minimum complete years per test"
    )

    ap.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="FDR significance level"
    )

    args = ap.parse_args()

    root = (
        Path(args.root).resolve()
        if args.root
        else Path(__file__).resolve().parent
    )

    files = sorted(
        (root / "Cleaned").glob(
            "*/*_clean.csv"
        )
    )

    if not files:

        sys.exit(
            f"No Cleaned/<State>/<State>_clean.csv "
            f"files found in {root}. "
            "Run clean_nasa_data.py first."
        )

    rows = []

    for file in files:

        state = state_name(
            file.parent.name
        )

        df = pd.read_csv(
            file,
            index_col=0,
            parse_dates=True
        ).select_dtypes(
            include=["number"]
        )

        for factor in df.columns:

            family = factor_family(factor)

            how = (
                "sum"
                if family == "precipitation"
                else "mean"
            )

            for period in PERIODS:

                values = aggregate_period(
                    df[factor],
                    period,
                    how
                ).dropna()

                n = len(values)

                if n < args.min_years:
                    continue

                years = values.index.to_numpy(
                    dtype=float
                )

                y = values.to_numpy(
                    dtype=float
                )

                slope, intercept, low, high = theilslopes(
                    y,
                    years,
                    alpha=0.95
                )

                tau, z, p, acf_factor = hamed_rao_mk(y)

                slope_decade = float(
                    slope * 10
                )

                mean = float(
                    np.mean(y)
                )

                unit = (
                    "mm/year"
                    if family == "precipitation"
                    and period == "annual"
                    else "mm/period"
                    if family == "precipitation"
                    else "m³/m³"
                    if family == "soil_moisture"
                    else "°C"
                    if family == "temperature"
                    else ""
                )

                rows.append({

                    "variable": family,
                    "factor": factor,
                    "state": state,
                    "period": period,

                    "first_year": int(years.min()),
                    "last_year": int(years.max()),
                    "n_years": n,

                    "mean": mean,
                    "std": float(
                        np.std(y, ddof=1)
                    ),

                    "unit": unit,

                    "slope_per_decade": slope_decade,

                    "ci95_low_per_decade": float(
                        low * 10
                    ),

                    "ci95_high_per_decade": float(
                        high * 10
                    ),

                    "kendall_tau": tau,
                    "mk_z": z,
                    "p_value": p,

                    "autocorr_variance_factor": acf_factor,

                    "direction": (
                        "up"
                        if slope > 0
                        else "down"
                        if slope < 0
                        else "flat"
                    )
                })

    result = pd.DataFrame(rows)

    if result.empty:

        sys.exit(
            "No factors had enough complete "
            "annual/seasonal observations."
        )

    result[
        "standardized_slope_per_decade"
    ] = (
        result["slope_per_decade"]
        / result["std"].replace(0, np.nan)
    )

    result["q_value_fdr"] = np.nan

    for period, idx in result.groupby(
        "period"
    ).groups.items():

        pvals = result.loc[
            idx,
            "p_value"
        ].to_numpy(dtype=float)

        result.loc[
            idx,
            "q_value_fdr"
        ] = multipletests(
            pvals,
            alpha=args.alpha,
            method="fdr_bh"
        )[1]

    result["significant_fdr"] = (
        result["q_value_fdr"] < args.alpha
    )

    result["significance_label"] = np.where(
        result.significant_fdr,
        "significant",
        "not_significant"
    )

    result = add_robustness(result)

    result = add_importance_indicators(
        result
    )

    out = (
        root
        / "Cleaned"
        / "Significance"
    )

    figs = out / "figures"

    figs.mkdir(
        parents=True,
        exist_ok=True
    )

    result.sort_values(
        [
            "period",
            "variable",
            "factor",
            "state"
        ]
    ).to_csv(
        out / "significance_table.csv",
        index=False,
        float_format="%.8g"
    )

    for period in PERIODS:

        filename = (
            "annual_significance_heatmap.png"
            if period == "annual"
            else
            f"seasonal_significance_heatmap_{period}.png"
        )

        plot_heatmap(
            result,
            period,
            figs / filename
        )

    annual = result[
        result.period == "annual"
    ].copy()

    series_dir = (
        figs / "individual_time_series"
    )

    series_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    projection_rows = []
    importance_rows = []

    for file in files:

        state = state_name(
            file.parent.name
        )

        raw = pd.read_csv(
            file,
            parse_dates=["date"]
        ).set_index("date")

        numeric = raw.select_dtypes(
            include=["number"]
        )

        for factor in numeric.columns:

            values = build_annual_series(
                numeric,
                factor
            )

            if len(values) < args.min_years:
                continue

            match = annual[
                (annual.state == state)
                & (annual.factor == factor)
            ]

            if match.empty:
                continue

            row = match.iloc[0]

            safe_factor = re.sub(
                r"[^A-Za-z0-9_.-]+",
                "_",
                factor
            )

            plot_path = (
                series_dir
                / f"{state.replace(' ', '')}_{safe_factor}.png"
            )

            fy, pv, pl, ph = plot_factor_series(
                values,
                row,
                plot_path,
                horizon=5
            )

            for yr, value, lo, hi in zip(
                fy,
                pv,
                pl,
                ph
            ):

                projection_rows.append({

                    "state": state,
                    "factor": factor,
                    "year": int(yr),

                    "projected_value": float(value),

                    "prediction_low_95_approx": float(lo),
                    "prediction_high_95_approx": float(hi),

                    "scenario": "historical_trend_continues"
                })

            half = len(values) // 2

            first = values.iloc[:half]
            second = values.iloc[half:]

            first_slope = (
                theilslopes(
                    first.to_numpy(),
                    first.index.to_numpy(dtype=float)
                ).slope
                if len(first) >= 5
                else np.nan
            )

            second_slope = (
                theilslopes(
                    second.to_numpy(),
                    second.index.to_numpy(dtype=float)
                ).slope
                if len(second) >= 5
                else np.nan
            )

            agreement = (
                bool(
                    np.sign(first_slope)
                    == np.sign(second_slope)
                )
                if np.isfinite(first_slope)
                and np.isfinite(second_slope)
                else np.nan
            )

            importance_rows.append({

                "state": state,
                "factor": factor,
                "family": factor_family(factor),

                "standardized_trend_magnitude_abs_sd_per_decade": (
                    abs(float(row.standardized_slope_per_decade))
                    if pd.notna(row.standardized_slope_per_decade)
                    else np.nan
                ),

                "direction_consistent_across_halves": agreement,

                "historical_significance_fdr": bool(
                    row.significant_fdr
                ),

                "cross_model_agreement": row.model_agreement,

                "robust_cross_model": bool(
                    row.robust_cross_model
                ),

                "interpretation_note": (
                    "Magnitude, persistence, significance "
                    "and source agreement are separate indicators; "
                    "none establishes causation."
                )
            })

    pd.DataFrame(
        projection_rows
    ).to_csv(
        out / "five_year_trend_continuation.csv",
        index=False,
        float_format="%.8g"
    )

    pd.DataFrame(
        importance_rows
    ).to_csv(
        out / "environmental_importance_indicators.csv",
        index=False,
        float_format="%.8g"
    )

    print(
        "\nANNUAL TREND SIGNIFICANCE "
        "(Hamed-Rao MK; Benjamini-Hochberg FDR)\n"
    )

    cols = [
        "state",
        "factor",
        "slope_per_decade",
        "ci95_low_per_decade",
        "ci95_high_per_decade",
        "p_value",
        "q_value_fdr",
        "significance_label",
        "robust_cross_model"
    ]

    print(
        annual[cols].sort_values(
            ["factor", "state"]
        ).to_string(
            index=False,
            float_format=lambda x: f"{x:.4g}"
        )
    )

    print(
        f"\nSaved {len(result)} tests to "
        f"{out}/significance_table.csv"
    )

    print(
        f"Figures saved to {figs}/"
    )

    print(
        "\nReminder: significance is not the same "
        "as environmental importance or causation."
    )


if __name__ == "__main__":
    main()