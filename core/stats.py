"""Trend statistics: seasonal Mann-Kendall test + Sen's slope (Hirsch et al., 1982).

Why this method: monthly Earth-science data has a strong yearly cycle. The seasonal
version compares each calendar month only with the same month in other years
(January vs January, ...), so the cycle cannot fake a trend, and partial years
(e.g. a record that starts in June) do no harm.
"""
import math

import numpy as np

ALPHA = 0.05          # "significant" means p < 0.05
SHORT_RECORD_YEARS = 10


def _norm_cdf(z):
    return 0.5 * math.erfc(-z / math.sqrt(2))


def seasonal_trend(df, alpha=ALPHA):
    """df: DataFrame with [date, value], monthly. Returns a dict, or None if too short.

    slope_per_year: Sen's slope, in the data's unit per year
    p_value:        two-sided, from the seasonal Mann-Kendall Z statistic
    ci_per_year:    (lo, hi) confidence interval for the slope
    """
    d = df.sort_values("date")
    x = d["value"].to_numpy(dtype=float)
    years = d["date"].dt.year.to_numpy()
    months = d["date"].dt.month.to_numpy()

    S, var, slopes = 0.0, 0.0, []
    for m in range(1, 13):
        sel = months == m
        v, yr = x[sel], years[sel]
        n = len(v)
        if n < 3:
            continue
        i, j = np.triu_indices(n, 1)
        dv, dy = v[j] - v[i], yr[j] - yr[i]
        S += float(np.sign(dv).sum())
        slopes.append(dv / dy)
        _, ties = np.unique(v, return_counts=True)
        var += (n * (n - 1) * (2 * n + 5) - np.sum(ties * (ties - 1) * (2 * ties + 5))) / 18.0

    if not slopes or var <= 0:
        return None
    slopes = np.sort(np.concatenate(slopes))
    N = len(slopes)

    z = 0.0 if S == 0 else (S - 1) / math.sqrt(var) if S > 0 else (S + 1) / math.sqrt(var)
    p = 2 * (1 - _norm_cdf(abs(z)))

    sen = float(np.median(slopes))
    c = 1.959964 * math.sqrt(var)  # 95% interval
    lo = float(slopes[max(0, int(math.floor((N - c) / 2)))])
    hi = float(slopes[min(N - 1, int(math.ceil((N + c) / 2)))])

    t = years + (months - 1) / 12.0                       # decimal years
    span = float(t.max() - t.min())
    intercept = float(x.mean() - sen * t.mean())          # line passes through the mean
    first, last = d["date"].iloc[0], d["date"].iloc[-1]
    line_y = [intercept + sen * t.min(), intercept + sen * t.max()]

    return {
        "slope_per_year": sen,
        "ci_per_year": (lo, hi),
        "p_value": float(p),
        "significant": bool(p < alpha),
        "direction": "up" if sen > 0 else "down" if sen < 0 else "flat",
        "years": round(span, 1),
        "start_year": int(first.year),
        "end_year": int(last.year),
        "total_change": sen * span,
        "line": {"x": [first.strftime("%Y-%m-%d"), last.strftime("%Y-%m-%d")],
                 "y": [round(v, 3) for v in line_y]},
    }
