
from pathlib import Path
from copy import deepcopy

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ==========================================================
# 1. CONFIGURATION
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_FILE = BASE_DIR / "unified_environmental_dataset.csv"

OUTPUT_DIR = BASE_DIR / "Integrated_AI_Results"
OUTPUT_DIR.mkdir(exist_ok=True)

LOOKBACK = 12
FORECAST_HORIZON = 12

EPOCHS = 200
BATCH_SIZE = 64
LEARNING_RATE = 0.001
PATIENCE = 20

SEED = 42

torch.manual_seed(SEED)
np.random.seed(SEED)

DEVICE = torch.device("cpu")

print("Device:", DEVICE)


# ==========================================================
# 2. LOAD HISTORICAL DATA
# ==========================================================

print("\nLoading historical environmental observations...")

df = pd.read_csv(DATA_FILE)

df["date"] = pd.to_datetime(df["date"])

df = df[
    df["record_type"] == "historical_observation"
].copy()

df["observed_value"] = pd.to_numeric(
    df["observed_value"],
    errors="coerce"
)

df = df[
    ["date", "state", "factor", "observed_value"]
]

df = df.sort_values(["state", "date", "factor"])

STATES = sorted(df["state"].unique())
FACTORS = sorted(df["factor"].unique())

print("States:", STATES)
print("Environmental factors:", len(FACTORS))
print("Factors:", FACTORS)

# One continuous monthly calendar
DATES = pd.date_range(
    start=df["date"].min(),
    end=df["date"].max(),
    freq="MS"
)

# Convert long format into one 16-variable panel per state
PANELS = {}

for state in STATES:

    state_data = df[df["state"] == state]

    panel = state_data.pivot(
        index="date",
        columns="factor",
        values="observed_value"
    )

    panel = panel.reindex(
        index=DATES,
        columns=FACTORS
    )

    PANELS[state] = panel


# ==========================================================
# 3. CHRONOLOGICAL TRAIN / VALIDATION / TEST SPLIT
# ==========================================================

TARGET_DATES = DATES[LOOKBACK:]

n_dates = len(TARGET_DATES)

train_end = int(n_dates * 0.70)
validation_end = int(n_dates * 0.85)

TRAIN_END_DATE = TARGET_DATES[train_end]
VALIDATION_END_DATE = TARGET_DATES[validation_end]

print("\nChronological split:")
print("Training ends:", TRAIN_END_DATE.date())
print("Validation ends:", VALIDATION_END_DATE.date())

# Calculate scaling parameters using training-period data only
training_values = pd.concat([
    panel.loc[panel.index < TRAIN_END_DATE]
    for panel in PANELS.values()
])

MEANS = training_values.mean().fillna(0).to_numpy()
STDS = training_values.std().replace(0, 1).fillna(1).to_numpy()

N_FACTORS = len(FACTORS)
N_STATES = len(STATES)

STATE_INDEX = {
    state: i for i, state in enumerate(STATES)
}


# ==========================================================
# 4. CREATE MULTIVARIATE TIME-SERIES WINDOWS
# ==========================================================

def create_sample(history, state, target_date, target):

    history = np.asarray(history, dtype=np.float32)

    missing_mask = np.isnan(history)

    normalized = (history - MEANS) / STDS

    # Missing input values are represented by zero
    # after normalization, with a separate missingness mask.
    normalized = np.nan_to_num(
        normalized,
        nan=0.0
    )

    state_vector = np.zeros(N_STATES, dtype=np.float32)

    state_vector[STATE_INDEX[state]] = 1.0

    month = target_date.month

    calendar_features = np.array([
        np.sin(2 * np.pi * month / 12),
        np.cos(2 * np.pi * month / 12)
    ], dtype=np.float32)

    features = np.concatenate([
        normalized.flatten(),
        missing_mask.astype(np.float32).flatten(),
        state_vector,
        calendar_features
    ])

    target = np.asarray(target, dtype=np.float32)

    target_mask = ~np.isnan(target)

    normalized_target = (target - MEANS) / STDS

    normalized_target = np.nan_to_num(
        normalized_target,
        nan=0.0
    )

    return (
        features,
        normalized_target,
        target_mask.astype(np.float32)
    )


X_LIST = []
Y_LIST = []
MASK_LIST = []
META = []

for state, panel in PANELS.items():

    values = panel.to_numpy(dtype=np.float64)

    for i in range(LOOKBACK, len(DATES)):

        target_date = DATES[i]

        history = values[i - LOOKBACK:i]
        target = values[i]

        x, y, mask = create_sample(
            history,
            state,
            target_date,
            target
        )

        X_LIST.append(x)
        Y_LIST.append(y)
        MASK_LIST.append(mask)

        META.append({
            "date": target_date,
            "state": state
        })


X = np.asarray(X_LIST, dtype=np.float32)
Y = np.asarray(Y_LIST, dtype=np.float32)
MASK = np.asarray(MASK_LIST, dtype=np.float32)

META = pd.DataFrame(META)

print("\nTraining samples:", len(X))
print("Input dimensions:", X.shape[1])
print("Output dimensions:", Y.shape[1])


# ==========================================================
# 5. CHRONOLOGICAL DATA SPLITS
# ==========================================================

dates = pd.to_datetime(META["date"])

train_mask = dates < TRAIN_END_DATE

validation_mask = (
    (dates >= TRAIN_END_DATE) &
    (dates < VALIDATION_END_DATE)
)

test_mask = dates >= VALIDATION_END_DATE


def select_data(mask):

    indices = np.where(mask.to_numpy())[0]

    return (
        torch.tensor(X[indices], dtype=torch.float32),
        torch.tensor(Y[indices], dtype=torch.float32),
        torch.tensor(MASK[indices], dtype=torch.float32)
    )


X_train, Y_train, M_train = select_data(train_mask)
X_val, Y_val, M_val = select_data(validation_mask)
X_test, Y_test, M_test = select_data(test_mask)

print("Train:", len(X_train))
print("Validation:", len(X_val))
print("Test:", len(X_test))


# ==========================================================
# 6. ONE SHARED MULTI-OUTPUT NEURAL NETWORK
# ==========================================================

INPUT_SIZE = X.shape[1]


class EnvironmentalNetwork(nn.Module):

    def __init__(self):

        super().__init__()

        self.network = nn.Sequential(

            nn.Linear(INPUT_SIZE, 128),
            nn.ReLU(),
            nn.Dropout(0.15),

            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.10),

            nn.Linear(64, N_FACTORS)
        )

    def forward(self, x):

        return self.network(x)


model = EnvironmentalNetwork().to(DEVICE)

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=0.001
)


# ==========================================================
# 7. MASKED MULTI-OUTPUT LOSS
# ==========================================================

def masked_loss(predictions, targets, mask):

    squared_error = (
        (predictions - targets) ** 2
    ) * mask

    counts = mask.sum(dim=0)

    per_factor_loss = (
        squared_error.sum(dim=0) /
        counts.clamp_min(1)
    )

    valid_factors = counts > 0

    return per_factor_loss[valid_factors].mean()


train_loader = DataLoader(
    TensorDataset(X_train, Y_train, M_train),
    batch_size=BATCH_SIZE,
    shuffle=True
)


# ==========================================================
# 8. TRAINING WITH VALIDATION AND EARLY STOPPING
# ==========================================================

best_validation_loss = float("inf")
best_weights = None
best_epoch = 0
patience_counter = 0

print("\nTraining the integrated environmental AI...")

for epoch in range(EPOCHS):

    model.train()

    training_losses = []

    for batch_x, batch_y, batch_mask in train_loader:

        optimizer.zero_grad()

        predictions = model(batch_x)

        loss = masked_loss(
            predictions,
            batch_y,
            batch_mask
        )

        loss.backward()

        optimizer.step()

        training_losses.append(loss.item())

    model.eval()

    with torch.no_grad():

        validation_predictions = model(X_val)

        validation_loss = masked_loss(
            validation_predictions,
            Y_val,
            M_val
        ).item()

    average_training_loss = np.mean(training_losses)

    if validation_loss < best_validation_loss:

        best_validation_loss = validation_loss

        best_weights = deepcopy(model.state_dict())

        best_epoch = epoch + 1

        patience_counter = 0

    else:

        patience_counter += 1

    if (epoch + 1) % 10 == 0:

        print(
            f"Epoch {epoch + 1:03d} | "
            f"Training loss: {average_training_loss:.5f} | "
            f"Validation loss: {validation_loss:.5f}"
        )

    if patience_counter >= PATIENCE:

        print("\nEarly stopping.")

        break


model.load_state_dict(best_weights)

print("Best epoch:", best_epoch)
print("Best validation loss:", best_validation_loss)


# ==========================================================
# 9. FINAL HELD-OUT TEST
# ==========================================================

model.eval()

with torch.no_grad():

    test_predictions = model(X_test).numpy()

test_actual = Y_test.numpy()
test_mask = M_test.numpy()

# Convert predictions back to original measurement units
test_predictions = test_predictions * STDS + MEANS
test_actual = test_actual * STDS + MEANS


prediction_rows = []
metric_rows = []
test_indices = np.arange(len(test_mask))

for factor_index, factor in enumerate(FACTORS):

    for state in STATES:

        observed = []
        predicted = []
        baseline = []
        result_dates = []

        # Find test samples belonging to this state
        indices = [
            i for i in test_indices
            if META.iloc[i]["state"] == state
        ]

        for sample_index in indices:

            # Skip missing observations for this factor
            if test_mask[sample_index, factor_index] == 0:
                continue

            actual_value = test_actual[
                sample_index, factor_index
            ]

            predicted_value = test_predictions[
                sample_index, factor_index
            ]

            meta_row = META.iloc[sample_index]

            state_panel = PANELS[state]

            target_position = DATES.get_loc(meta_row["date"])

            # Seasonal-naive baseline: same month one year earlier
            previous_position = target_position - 12

            if previous_position < 0:
                continue

            baseline_value = state_panel.iloc[
                previous_position
            ][factor]

            if pd.isna(baseline_value):
                continue

            observed.append(actual_value)
            predicted.append(predicted_value)
            baseline.append(baseline_value)
            result_dates.append(meta_row["date"])

            prediction_rows.append({
                "state": state,
                "date": meta_row["date"],
                "factor": factor,
                "actual": actual_value,
                "predicted": predicted_value,
                "baseline": baseline_value
            })

        if len(observed) == 0:
            continue

        observed = np.array(observed)
        predicted = np.array(predicted)
        baseline = np.array(baseline)

        mae = np.mean(np.abs(observed - predicted))
        rmse = np.sqrt(np.mean((observed - predicted) ** 2))

        baseline_mae = np.mean(
            np.abs(observed - baseline)
        )

        baseline_rmse = np.sqrt(
            np.mean((observed - baseline) ** 2)
        )

        metric_rows.append({
            "state": state,
            "factor": factor,
            "samples": len(observed),
            "MAE": mae,
            "RMSE": rmse,
            "Baseline_MAE": baseline_mae,
            "Baseline_RMSE": baseline_rmse
        })



# ==========================================================
# 10. RECURSIVE 12-MONTH FORECAST
# ==========================================================

print("\nGenerating 12-month forecasts...")

forecast_rows = []

for state, panel in PANELS.items():

    history = panel.to_numpy(dtype=np.float64).copy()

    state_vector = np.zeros(N_STATES, dtype=np.float32)

    state_vector[STATE_INDEX[state]] = 1.0

    latest_observation_date = DATES[-1]

    latest_precip_dates = panel[
        "precip_mm_month"
    ].dropna()

    last_precip_date = (
        latest_precip_dates.index.max()
        if len(latest_precip_dates) else pd.NaT
    )

    for step in range(FORECAST_HORIZON):

        recent_history = history[-LOOKBACK:]

        missing_mask = np.isnan(recent_history)

        normalized_history = (
            recent_history - MEANS
        ) / STDS

        normalized_history = np.nan_to_num(
            normalized_history,
            nan=0.0
        )

        next_date = (
            latest_observation_date +
            pd.DateOffset(months=step + 1)
        )

        month = next_date.month

        calendar_features = np.array([
            np.sin(2 * np.pi * month / 12),
            np.cos(2 * np.pi * month / 12)
        ], dtype=np.float32)

        model_input = np.concatenate([
            normalized_history.flatten(),
            missing_mask.astype(np.float32).flatten(),
            state_vector,
            calendar_features
        ])

        model_input = torch.tensor(
            model_input,
            dtype=torch.float32
        ).unsqueeze(0)

        with torch.no_grad():

            prediction = model(model_input).numpy()[0]

        prediction = prediction * STDS + MEANS

        for j, factor in enumerate(FACTORS):

            warning = ""

            if (
                factor == "precip_mm_month"
                and (
                    pd.isna(last_precip_date)
                    or (
                        latest_observation_date - last_precip_date
                    ).days > 62
                )
            ):

                warning = (
                    "LOW CONFIDENCE: precipitation "
                    "observations are outdated"
                )

            forecast_rows.append({

                "date": next_date,
                "state": state,
                "factor": factor,
                "predicted_value": prediction[j],
                "forecast_warning": warning
            })

        # Feed predictions into the next forecasting step
        history = np.vstack([
            history,
            prediction
        ])


# ==========================================================
# 11. EXPORT INDIVIDUAL SIGNIFICANCE DATA
# ==========================================================

SIGNIFICANCE_COLUMNS = [
    "slope_per_decade",
    "pct_per_decade",
    "direction",
    "p_value",
    "q_value_fdr",
    "significant_fdr",
    "significance_label",
    "kendall_tau",
    "ci95_low_per_decade",
    "ci95_high_per_decade"
]

available_significance = [
    column for column in SIGNIFICANCE_COLUMNS
    if column in df.columns
]

significance = df.merge(
    pd.read_csv(DATA_FILE)[
        ["state", "factor"] + available_significance
    ].drop_duplicates(["state", "factor"]),
    on=["state", "factor"],
    how="left"
)

significance = significance[
    ["state", "factor"] + available_significance
].drop_duplicates(["state", "factor"])

significance.to_csv(
    OUTPUT_DIR / "factor_significance.csv",
    index=False
)


# ==========================================================
# 12. SAVE EVERYTHING
# ==========================================================

pd.DataFrame(metric_rows).to_csv(
    OUTPUT_DIR / "model_test_metrics.csv",
    index=False
)

pd.DataFrame(prediction_rows).to_csv(
    OUTPUT_DIR / "historical_test_predictions.csv",
    index=False
)

pd.DataFrame(forecast_rows).to_csv(
    OUTPUT_DIR / "12_month_forecast.csv",
    index=False
)

torch.save({
    "model_state_dict": model.state_dict(),
    "factors": FACTORS,
    "states": STATES,
    "means": MEANS,
    "stds": STDS,
    "lookback": LOOKBACK,
    "best_epoch": best_epoch
}, OUTPUT_DIR / "environmental_ai_model.pth")


print("\n" + "=" * 60)
print("INTEGRATED ENVIRONMENTAL AI COMPLETE")
print("=" * 60)

print("\nTest metrics:")
print(pd.DataFrame(metric_rows).to_string(index=False))

print("\nForecast origin:", DATES[-1].date())
print(
    "Forecast period:",
    DATES[-1] + pd.DateOffset(months=1),
    "to",
    DATES[-1] + pd.DateOffset(months=12)
)

print("\nOutput directory:")
print(OUTPUT_DIR.resolve())
