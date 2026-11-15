# Data contracts

The app reads two files from `data/processed/`. `monthly.csv` is built from the bundled cleaned
monthly files in `data/cleaned/Alabama`, `data/cleaned/Texas`, and `data/cleaned/NewYork`.
Rebuild it from the project root with `python -m data_pipeline.build_dataset`.

## 1. `monthly.csv` - measurements (built by `python -m data_pipeline.build_dataset`)

| column | meaning |
|---|---|
| date | first day of the month, `YYYY-MM-DD` |
| state | `TX`, `AL` or `NY` |
| variable | `temperature`, `precipitation` or `soil_moisture` |
| value | the monthly value, in the unit below |
| unit | `°C`, `% of soil volume` or `mm/month` |
| source | `MERRA-2`, `GPM IMERG`, `FLDAS` or `NLDAS` |
| depth | optional, soil moisture only: `0-10cm`, `10-40cm`, `40-100cm`, `100-200cm` |

The pipeline uses monthly mean 2 m air temperature from `M2TMNXSLV_5_12_4_T2M`, monthly
precipitation from `precip_mm_month`, and all four FLDAS and NLDAS soil-moisture depths.
The cleaned soil-moisture values are fractions of soil volume and are converted once to percent
for the app's display unit. Missing precipitation values remain missing and are omitted, not
replaced with zero.

## 2. `hotspots.csv` - experimental model-based phenomena estimates

Build it with `python -m data_pipeline.build_hotspots`. The script loads the trained
`environmental_ai_model.pth`, recursively forecasts the 16 factors for the next 12 months, and
uses the forecast plus held-out model errors to estimate drought and flood risk. If the repository's
NASA model artifacts are unavailable, it uses the bundled copies in `data/models/`.

The inputs are state averages, so each map marker is placed at an approximate state center. It is
not a localized hotspot or a county-level hazard forecast. The estimates are experimental, are not
official alerts, and have not been calibrated as operational hazard probabilities.

The estimated risk combines model-error-based exceedance rates against month-specific historical
20th/80th percentile thresholds: hot temperature and low precipitation/soil moisture contribute
to drought risk; high precipitation and soil moisture contribute to flood risk. Validation errors
come from the held-out period. This is a risk signal, not a causal or operational flood/drought
model.

| column | meaning |
|---|---|
| state | `TX`, `AL` or `NY` |
| lat | latitude in decimal degrees, e.g. `31.2` |
| lon | longitude in decimal degrees, **negative for the US**, e.g. `-99.4` |
| phenomenon | `drought` or `flood` (keys live in `config.py` -> `PHENOMENA`) |
| probability | estimated risk from `0` to `1` (**not** a percentage), e.g. `0.58` |
| for_month | forecast month, stored as its first day, e.g. `2027-09-01` |

Format illustration only (not real predictions):

```
state,lat,lon,phenomenon,probability,for_month
TX,31.2,-99.3,drought,0.58,2027-09-01
```

Rules the app enforces (bad rows are skipped and logged, the rest still draw):
- lat/lon must fall inside the state's bounding box (this catches swapped lat/lon)
- `probability` must be between 0 and 1
- `phenomenon` and `state` must be one of the keys above
- if the file holds several months, the map shows the latest month for the chosen state

## 3. Chance of an event

The event-chance API also uses `environmental_ai_model.pth`. It selects the model's forecast for
the current or next available month and combines it with held-out prediction errors for the
selected state and factor. Those simulated values are compared with the historical 20th and 80th
percentiles for the forecast month. Precipitation and soil moisture estimate unusually dry/wet
months; temperature estimates unusually cool/hot months. Soil-moisture model values and errors
are converted to the app's percentage units before comparison.

These are experimental estimates, not official hazard alerts. The displayed usual rate is the
historical frequency of that threshold for the same calendar month; it is a reference rate, not
an independently validated model skill score.
