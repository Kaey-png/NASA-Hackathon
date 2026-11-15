# NASA-Hackathon
# Be an Earth System Trend Detective

### An integrated AI system for exploring environmental trends and forecasting future conditions across the United States.

**NASA Space Apps Challenge Project**

---

## About the Project

Environmental changes are interconnected. Soil moisture, precipitation, surface temperature, humidity and other environmental variables can influence one another and contribute to broader environmental patterns.

However, understanding these relationships across different geographical regions can be challenging when environmental datasets are distributed across multiple sources and contain different variables, time ranges and measurement formats.

**Be an Earth System Trend Detective** aims to make environmental data easier to explore, understand and investigate.

Our project brings together historical environmental observations, statistical trend analysis and an integrated multi-output AI forecasting model to investigate environmental conditions across three US states:

- Alabama
- New York
- Texas

Rather than examining each environmental variable in isolation, our approach uses a shared model to learn patterns across multiple environmental factors and generate predictions for them together.

## What We Are Building

The project consists of two major components.

### 1. Integrated Environmental AI

Our AI component uses a shared multivariate neural network built with PyTorch.

The model processes historical observations from 16 environmental factors across three states.

Its architecture uses:

- A 12-month historical observation window.
- State identification features.
- Seasonal calendar features.
- Missing-data masks.
- A shared neural network with multiple output neurons, one for each environmental factor.

The model is designed to learn shared patterns across environmental variables and geographical regions.

It generates experimental predictions for a 12-month forecast horizon.

### 2. Interactive Environmental Mapping

The interactive visualization component is designed to make the model's findings accessible.

Planned features include:

**Historical Environmental Hotspot Map**

An interactive map displaying the statistical trends and significance of individual environmental factors across Alabama, New York and Texas.

**Future Environmental Conditions Map**

A visualization of model-generated future environmental conditions, allowing users to explore predicted changes across the three states.

The goal is to let users investigate environmental patterns without needing to manually analyze large datasets.

## Environmental Factors

The unified dataset contains 16 environmental variables:

| Category | Environmental variables |
|---|---|
| Soil moisture | FLDAS soil moisture at four depth ranges |
| Soil moisture | NLDAS soil moisture at four depth ranges |
| Temperature | Maximum, minimum and mean temperature |
| Atmospheric conditions | Dew point, wet-bulb temperature and surface temperature |
| Other climate indicators | Diurnal temperature range |
| Precipitation | Monthly precipitation |

The dataset combines observations from September 1982 through September 2026 for most variables. Precipitation has a shorter observation period, ending in September 2025.

## AI Methodology

### Data preparation

The original environmental observations are organized into a unified monthly dataset.

The preparation process includes:

1. Filtering historical observations.
2. Organizing observations by state, date and environmental factor.
3. Converting the data into multivariate time-series panels.
4. Handling missing observations using explicit missing-data masks.
5. Normalizing measurements using training-period statistics.

Missing precipitation measurements are not treated as zero.

### Model architecture

The project uses a single shared multi-output neural network.

Instead of training a completely separate neural network for every environmental factor and state, the model learns from the combined training samples.

**Architecture:**

- Input layer: historical environmental observations, missingness indicators, state features and seasonal features.
- Hidden layer 1: 128 neurons with ReLU activation.
- Hidden layer 2: 64 neurons with ReLU activation.
- Output layer: 16 neurons representing the environmental factors.

The model uses AdamW optimization, dropout regularization, masked loss and early stopping.

### Model evaluation

The dataset is divided chronologically into:

- 70% training data.
- 15% validation data.
- 15% held-out test data.

Evaluation includes:

- Mean Absolute Error (MAE).
- Root Mean Squared Error (RMSE).
- Coefficient of Determination (R²).
- Seasonal-naive baseline comparison.

The forecasting system currently generates predictions recursively over a 12-month horizon. Multi-step forecast performance requires further validation before the predictions can be considered reliable.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core development |
| PyTorch | Neural network development and training |
| Pandas | Environmental data processing |
| NumPy | Numerical computation |
| Scikit-learn | Model evaluation |
| Interactive mapping tools | Environmental visualization |

## Project Structure

```text
NASA-Hackathon/
│
└── DataAnalysis/
    └── Cleaned/
        └── Unified/
            │
            ├── unified_environmental_dataset.csv
            ├── integrated_environmental_ai.py
            │
            └── Integrated_AI_Results/
                ├── environmental_ai_model.pth
                ├── model_test_metrics.csv
                ├── historical_test_predictions.csv
                ├── 12_month_forecast.csv
                └── factor_significance.csv
```

## Running the AI Model

### Requirements

- Python
- PyTorch
- Pandas
- NumPy
- Scikit-learn

### Installation

Clone the repository:

```bash
git clone YOUR_REPOSITORY_URL
```

Navigate to the unified data directory:

```bash
cd NASA-Hackathon/DataAnalysis/Cleaned/Unified
```

Install the required packages:

```bash
python -m pip install torch pandas numpy scikit-learn
```

Run the model:

```bash
python integrated_environmental_ai.py
```

The model reads `unified_environmental_dataset.csv` and saves its outputs in:

```text
Integrated_AI_Results/
```

## Generated Outputs

| Output | Description |
|---|---|
| `environmental_ai_model.pth` | Saved PyTorch model parameters and associated configuration data |
| `model_test_metrics.csv` | Test evaluation metrics |
| `historical_test_predictions.csv` | Historical test predictions alongside observed values |
| `12_month_forecast.csv` | Experimental 12-month environmental predictions |
| `factor_significance.csv` | Environmental trend statistics for mapping |

## Important Limitations

This project is an experimental environmental analysis and forecasting system.

- Its geographical coverage is currently limited to Alabama, New York and Texas.
- Predictions represent state-level environmental estimates, not county-level or city-level forecasts.
- Historical statistical significance does not establish causation.
- Precipitation observations cover a shorter period than most other variables.
- Recursive forecasting can accumulate prediction errors over time.
- The model's 12-month forecasting performance must be assessed through appropriate multi-step validation.
- The outputs are not official NASA forecasts or substitutes for operational weather forecasting.

## Our Goal

We want to make environmental data more accessible, connect multiple environmental indicators within one analytical framework, and give people an interactive way to investigate historical trends and possible future environmental conditions.

**Explore the data. Investigate the patterns. Become an Earth System Trend Detective.**

---

*Developed for the NASA Space Apps Challenge.*
