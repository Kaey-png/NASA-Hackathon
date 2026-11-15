"""Fixed choices the app offers. The data CSV must use these exact keys."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "processed" / "monthly.csv"
HOTSPOTS_PATH = BASE_DIR / "data" / "processed" / "hotspots.csv"

# Use the state-level model estimates written to data/processed/hotspots.csv.
USE_DEMO_HOTSPOTS = False
DEMO_HOTSPOTS_PATH = BASE_DIR / "data" / "placeholder" / "hotspots_demo.csv"

# view = where the 3D map flies to; bbox = [south, west, north, east], used to catch
# hotspot rows whose lat/lon are swapped or in the wrong state.
STATES = [
    {"code": "TX", "name": "Texas", "view": {"lat": 31.2, "lon": -99.3, "zoom": 5.0},
     "bbox": [25.8, -106.7, 36.5, -93.5]},
    {"code": "AL", "name": "Alabama", "view": {"lat": 32.8, "lon": -86.8, "zoom": 6.1},
     "bbox": [30.1, -88.5, 35.0, -84.9]},
    {"code": "NY", "name": "New York", "view": {"lat": 42.9, "lon": -75.5, "zoom": 6.0},
     "bbox": [40.5, -79.8, 45.1, -71.8]},
]

# Events the model can predict. The hotspot file's `phenomenon` column must use these keys.
PHENOMENA = {
    "drought": {"label": "Drought risk", "color": "#ffb86b"},
    "flood": {"label": "Flood risk", "color": "#60a5fa"},
}

PARAMETERS = [
    {
        "key": "temperature",
        "label": "Temperature",
        "definition": "How warm the air 2 meters above the ground is, averaged over each month.",
        "source": "NASA MERRA-2, monthly 2 m air temperature",
    },
    {
        "key": "precipitation",
        "label": "Precipitation",
        "definition": "How much rain and snow falls, added up over each month.",
        "source": "NASA GPM IMERG, monthly state average",
    },
    {
        "key": "soil_moisture",
        "label": "Soil moisture",
        "definition": "How much water the soil holds, as a share of the soil's volume. "
                      "Higher means wetter.",
        "source": "NASA FLDAS and NLDAS land models, state average",
        # The two models measure soil water slightly differently, so compare
        # their direction of change, not their exact levels.
        "note": "The two models differ in their absolute levels, so compare the direction of change.",
        "depths": [
            {"key": "0-10cm", "label": "Surface soil (0–10 cm)"},
            {"key": "10-40cm", "label": "Root zone (10–40 cm)"},
            {"key": "40-100cm", "label": "Deep soil (40–100 cm)"},
            {"key": "100-200cm", "label": "Very deep (100–200 cm)"},
        ],
    },
]
