
#!/usr/bin/env python3

"""
NASA Hackathon - Unified Environmental Dataset

Combines:
1. Cleaned monthly environmental observations
2. Annual trend analysis
3. Annual statistical significance
4. Environmental importance indicators
5. Five-year trend-continuation scenarios

Run:
    python unify_environmental_data.py
"""

from pathlib import Path
import sys

import pandas as pd


BASE = Path(__file__).resolve().parent
CLEANED = BASE / "Cleaned"

OUTPUT = CLEANED / "Unified"
OUTPUT.mkdir(parents=True, exist_ok=True)


def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found: {path}"
        )

    return pd.read_csv(path)


def main():

    print("\nNASA ENVIRONMENTAL DATA UNIFICATION")
    print("=" * 45)

    # ------------------------------------------------
    # 1. Load the cleaned environmental observations
    # ------------------------------------------------

    observations = load_csv(
        CLEANED / "all_states_clean.csv"
    )

    observations["date"] = pd.to_datetime(
        observations["date"],
        errors="coerce"
    )

    observations = observations.dropna(
        subset=["date", "state"]
    )

    observations["year"] = (
        observations["date"].dt.year
    )

    print(
        f"Loaded {len(observations)} monthly observations."
    )

    # Identify environmental factors
    excluded = {
        "date",
        "state",
        "season",
        "year"
    }

    factors = [
        col for col in observations.columns
        if col not in excluded
    ]

    # Convert observations from wide to long format
    monthly = observations.melt(
        id_vars=[
            "date",
            "year",
            "state",
            "season"
        ],
        value_vars=factors,
        var_name="factor",
        value_name="observed_value"
    )

    monthly["record_type"] = (
        "historical_observation"
    )

    monthly["temporal_resolution"] = "monthly"

    # ------------------------------------------------
    # 2. Load annual observed values
    # ------------------------------------------------

    annual_values = load_csv(
        CLEANED / "Trends" / "annual_values.csv"
    )

    annual_values["year"] = (
        annual_values["year"].astype(int)
    )

    annual_values = annual_values.rename(
        columns={
            "value": "annual_observed_value"
        }
    )

    # ------------------------------------------------
    # 3. Load annual trend analysis
    # ------------------------------------------------

    trends = load_csv(
        CLEANED / "Trends" / "trend_table.csv"
    )

    trends = trends[
        trends["period"].astype(str).str.lower()
        == "annual"
    ].copy()

    trend_columns = [
        "state",
        "factor",
        "slope_per_decade",
        "pct_per_decade",
        "direction",
        "first_year",
        "last_year",
        "n_years"
    ]

    trends = trends[
        [
            col for col in trend_columns
            if col in trends.columns
        ]
    ]

    # ------------------------------------------------
    # 4. Load annual significance results
    # ------------------------------------------------

    significance = load_csv(
        CLEANED
        / "Significance"
        / "significance_table.csv"
    )

    significance = significance[
        significance["period"].astype(str).str.lower()
        == "annual"
    ].copy()

    significance_columns = [
        "state",
        "factor",
        "p_value",
        "q_value_fdr",
        "significant_fdr",
        "significance_label",
        "kendall_tau",
        "ci95_low_per_decade",
        "ci95_high_per_decade",
        "standardized_slope_per_decade",
        "model_agreement",
        "robust_cross_model"
    ]

    significance = significance[
        [
            col for col in significance_columns
            if col in significance.columns
        ]
    ]

    # ------------------------------------------------
    # 5. Load environmental importance indicators
    # ------------------------------------------------

    importance = load_csv(
        CLEANED
        / "Significance"
        / "environmental_importance_indicators.csv"
    )

    # ------------------------------------------------
    # 6. Load five-year trend scenarios
    # ------------------------------------------------

    projections = load_csv(
        CLEANED
        / "Significance"
        / "five_year_trend_continuation.csv"
    )

    # ------------------------------------------------
    # 7. Attach annual observed values to monthly data
    # ------------------------------------------------

    monthly = monthly.merge(
        annual_values,
        on=["state", "factor", "year"],
        how="left"
    )

    # ------------------------------------------------
    # 8. Attach annual trend information
    # ------------------------------------------------

    monthly = monthly.merge(
        trends,
        on=["state", "factor"],
        how="left",
        validate="many_to_one"
    )

    # ------------------------------------------------
    # 9. Attach annual significance information
    # ------------------------------------------------

    monthly = monthly.merge(
        significance,
        on=["state", "factor"],
        how="left",
        validate="many_to_one"
    )

    # ------------------------------------------------
    # 10. Attach importance indicators
    # ------------------------------------------------

    monthly = monthly.merge(
        importance,
        on=["state", "factor"],
        how="left",
        validate="many_to_one"
    )

    # ------------------------------------------------
    # 11. Prepare projection records
    # ------------------------------------------------

    projected = projections.copy()

    projected["year"] = (
        projected["year"].astype(int)
    )

    projected["date"] = pd.to_datetime(
        projected["year"].astype(str) + "-01-01"
    )

    projected["season"] = "ANNUAL"

    projected["observed_value"] = pd.NA
    projected["annual_observed_value"] = pd.NA

    projected["record_type"] = (
        "future_projection"
    )

    projected["temporal_resolution"] = "annual"

    projected = projected.rename(
        columns={
            "projected_value": "scenario_value"
        }
    )

    # Add the same trend and significance metadata
    # to the projected records.

    projected = projected.merge(
        trends,
        on=["state", "factor"],
        how="left",
        validate="many_to_one"
    )

    projected = projected.merge(
        significance,
        on=["state", "factor"],
        how="left",
        validate="many_to_one"
    )

    projected = projected.merge(
        importance,
        on=["state", "factor"],
        how="left",
        validate="many_to_one"
    )

    # ------------------------------------------------
    # 12. Combine historical and projected records
    # ------------------------------------------------

    # Use the union of columns so both record types
    # retain all available information.

    unified = pd.concat(
        [
            monthly,
            projected
        ],
        ignore_index=True,
        sort=False
    )

    unified = unified.sort_values(
        [
            "state",
            "factor",
            "date",
            "record_type"
        ]
    )

    # ------------------------------------------------
    # 13. Add dataset metadata
    # ------------------------------------------------

    unified["dataset_version"] = "1.0"

    unified["projection_warning"] = (
        unified["record_type"]
        == "future_projection"
    )

    # ------------------------------------------------
    # 14. Save unified dataset
    # ------------------------------------------------

    output_file = (
        OUTPUT / "unified_environmental_dataset.csv"
    )

    unified.to_csv(
        output_file,
        index=False
    )

    # Also preserve the historical observations
    # and future scenarios as separate convenient files.

    monthly.to_csv(
        OUTPUT / "historical_environmental_dataset.csv",
        index=False
    )

    projected.to_csv(
        OUTPUT / "future_projection_dataset.csv",
        index=False
    )

    # ------------------------------------------------
    # 15. Generate a validation report
    # ------------------------------------------------

    report = []

    report.append(
        "NASA HACKATHON - DATA UNIFICATION REPORT"
    )

    report.append("=" * 45)

    report.append(
        f"Total unified records: {len(unified)}"
    )

    report.append(
        f"Historical monthly records: {len(monthly)}"
    )

    report.append(
        f"Future projection records: {len(projected)}"
    )

    report.append(
        f"Environmental factors: {len(factors)}"
    )

    report.append(
        f"States: {', '.join(sorted(observations['state'].unique()))}"
    )

    report.append("")

    report.append("Records by type:")

    report.append(
        unified["record_type"]
        .value_counts()
        .to_string()
    )

    report.append("")

    report.append("Records by state:")

    report.append(
        unified.groupby(
            ["state", "record_type"]
        ).size().to_string()
    )

    report.append("")

    report.append(
        "Missing observed values in historical records: "
        + str(
            monthly["observed_value"].isna().sum()
        )
    )

    report.append(
        "Missing significance labels in historical records: "
        + str(
            monthly["significance_label"].isna().sum()
        )
    )

    report.append("")

    report.append(
        "IMPORTANT: Future values are trend-continuation "
        "scenarios, not observed measurements or "
        "formal climate forecasts."
    )

    report_file = (
        OUTPUT / "unification_report.txt"
    )

    report_file.write_text(
        "\n".join(report),
        encoding="utf-8"
    )

    # ------------------------------------------------
    # 16. Display results
    # ------------------------------------------------

    print("\nUNIFICATION COMPLETED")
    print("=" * 45)

    print(
        f"Historical records: {len(monthly)}"
    )

    print(
        f"Projection records: {len(projected)}"
    )

    print(
        f"Total unified records: {len(unified)}"
    )

    print(
        f"\nOutput folder: {OUTPUT}"
    )

    print(
        "\nFiles created:"
    )

    print(
        "1. unified_environmental_dataset.csv"
    )

    print(
        "2. historical_environmental_dataset.csv"
    )

    print(
        "3. future_projection_dataset.csv"
    )

    print(
        "4. unification_report.txt"
    )


if __name__ == "__main__":
    main()
