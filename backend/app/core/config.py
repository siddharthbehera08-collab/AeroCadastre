import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT_DEFAULT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT_DEFAULT / ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    APP_NAME: str = "SIH26012 AeroCadastre GeoAI & PostGIS Platform API"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Database & Security loaded from environment variables (no hardcoded passwords)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres@127.0.0.1:5432/aerocadastre",
    )
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    REQUIRE_AUTH_FOR_MUTATIONS: bool = (
        os.getenv("REQUIRE_AUTH_FOR_MUTATIONS", "false").lower() == "true"
    )

    # Coordinate Reference Systems
    DEFAULT_GEOGRAPHIC_CRS: str = os.getenv("DEFAULT_GEOGRAPHIC_CRS", "EPSG:4326")
    DEFAULT_PROJECTED_CRS: str = os.getenv("DEFAULT_PROJECTED_CRS", "EPSG:32643")
    DEFAULT_SRID: int = 4326
    METRIC_SRID: int = 32643

    # Storage Directories on D: drive
    PROJECT_ROOT: Path = Path(os.getenv("PROJECT_ROOT", str(PROJECT_ROOT_DEFAULT))).resolve()

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT_DEFAULT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def data_dir(self) -> Path:
        p = Path(os.getenv("DATA_DIR", str(self.PROJECT_ROOT / "data"))).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def synthetic_data_dir(self) -> Path:
        p = Path(
            os.getenv("SYNTHETIC_DATA_DIR", str(self.PROJECT_ROOT / "synthetic_data"))
        ).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def models_dir(self) -> Path:
        p = Path(os.getenv("MODELS_DIR", str(self.PROJECT_ROOT / "models"))).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def experiments_dir(self) -> Path:
        p = Path(
            os.getenv("EXPERIMENTS_DIR", str(self.PROJECT_ROOT / "experiments"))
        ).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def outputs_dir(self) -> Path:
        p = Path(os.getenv("OUTPUTS_DIR", str(self.PROJECT_ROOT / "outputs"))).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def logs_dir(self) -> Path:
        p = Path(os.getenv("LOGS_DIR", str(self.PROJECT_ROOT / "logs"))).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def database_dir(self) -> Path:
        p = Path(os.getenv("DATABASE_DIR", str(self.PROJECT_ROOT / "database"))).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def app_name(self) -> str:
        return self.APP_NAME

    @property
    def app_version(self) -> str:
        return self.APP_VERSION

    @property
    def database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    @property
    def secret_key(self) -> str:
        return self.SECRET_KEY

    @property
    def default_crs(self) -> str:
        return self.DEFAULT_GEOGRAPHIC_CRS

    @property
    def metric_crs(self) -> str:
        return self.DEFAULT_PROJECTED_CRS

    @property
    def default_srid(self) -> int:
        return self.DEFAULT_SRID

    @property
    def metric_srid(self) -> int:
        return self.METRIC_SRID

    @property
    def cors_origins(self) -> list[str]:
        raw = os.getenv("CORS_ORIGINS", "*")
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()

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
