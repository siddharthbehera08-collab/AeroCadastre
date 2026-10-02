import os
from pathlib import Path

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", "D:/SIH26012_AeroCadastre")).resolve()
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data"))).resolve()
SYNTHETIC_DATA_DIR = Path(os.getenv("SYNTHETIC_DATA_DIR", str(PROJECT_ROOT / "synthetic_data"))).resolve()
MODELS_DIR = Path(os.getenv("MODELS_DIR", str(PROJECT_ROOT / "models"))).resolve()
EXPERIMENTS_DIR = Path(os.getenv("EXPERIMENTS_DIR", str(PROJECT_ROOT / "experiments"))).resolve()
OUTPUTS_DIR = Path(os.getenv("OUTPUTS_DIR", str(PROJECT_ROOT / "outputs"))).resolve()
LOGS_DIR = Path(os.getenv("LOGS_DIR", str(PROJECT_ROOT / "logs"))).resolve()
DATABASE_DIR = Path(os.getenv("DATABASE_DIR", str(PROJECT_ROOT / "database"))).resolve()

for d in [DATA_DIR, SYNTHETIC_DATA_DIR, MODELS_DIR, EXPERIMENTS_DIR, OUTPUTS_DIR, LOGS_DIR, DATABASE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DEFAULT_SQLITE_URL = f"sqlite:///{(DATABASE_DIR / 'aerocadastre_postgis.db').as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)

DEFAULT_GEOGRAPHIC_CRS = os.getenv("DEFAULT_GEOGRAPHIC_CRS", "EPSG:4326")
DEFAULT_PROJECTED_CRS = os.getenv("DEFAULT_PROJECTED_CRS", "EPSG:32643")  # UTM Zone 43N (India)

LAND_USE_CLASSES = [
    "background",
    "residential",
    "commercial",
    "industrial",
    "agricultural",
    "vegetation",
    "water",
    "vacant",
    "road",
    "mixed_use",
]

BOUNDARY_TYPES = [
    "VISIBLE",
    "INFERRED",
    "REFERENCE",
    "HUMAN_VERIFIED",
]

COUNCIL_ACTIONS = [
    "ACCEPT_FOR_REVIEW",
    "REQUIRES_VERIFICATION",
    "LOW_CONFIDENCE",
    "GEOMETRY_ERROR",
    "CONFLICT_DETECTED",
]
