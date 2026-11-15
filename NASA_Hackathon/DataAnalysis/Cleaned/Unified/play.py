
import pandas as pd

df = pd.read_csv("unified_environmental_dataset.csv")
df["date"] = pd.to_datetime(df["date"], errors="coerce")

hist = df[df["record_type"] == "historical_observation"].copy()

# A. Exact precipitation coverage
print("\nA. PRECIPITATION COVERAGE")

precip = hist[
    (hist["factor"] == "precip_mm_month") &
    (hist["observed_value"].notna())
]

for state, group in precip.groupby("state"):
    print(
        state,
        "| First:", group["date"].min(),
        "| Last:", group["date"].max(),
        "| Measurements:", len(group)
    )

# B. Missing annual values by year
print("\nB. MISSING ANNUAL VALUES BY YEAR")

for factor in sorted(hist["factor"].unique()):
    subset = hist[hist["factor"] == factor]
    missing_years = sorted(
        subset.loc[
            subset["annual_observed_value"].isna(), "year"
        ].unique()
    )

    if missing_years:
        print(factor, ":", missing_years)

# C. Precipitation measurements by year
print("\nC. PRECIPITATION MEASUREMENTS BY YEAR")

print(
    precip.groupby(precip["date"].dt.year)
    .size()
    .to_string()
)

# D. Check whether dates are continuous
print("\nD. DATE CONTINUITY")

for state in sorted(hist["state"].unique()):
    dates = sorted(hist[hist["state"] == state]["date"].unique())
    expected = pd.date_range(
        start=dates[0],
        end=dates[-1],
        freq="MS"
    )

    print(
        state,
        "| Expected months:", len(expected),
        "| Actual months:", len(dates),
        "| Missing dates:", len(set(expected) - set(dates))
    )

# E. Check whether observed values are duplicated
print("\nE. DUPLICATE OBSERVATIONS")

print(
    "Duplicate date/state/factor records:",
    hist.duplicated(["date", "state", "factor"]).sum()
)
