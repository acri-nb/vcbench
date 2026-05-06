import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
LAB_RUNS_DIR = DATA_DIR / "lab_runs"
PROCESSED_DIR = DATA_DIR / "processed"
REFERENCE_DIR = DATA_DIR / "reference"
TMP_DIR = PROJECT_ROOT / "qc-dashboard" / "api" / "app" / "tmp"
UPLOAD_DIR = TMP_DIR / "uploads"
AWS_DOWNLOAD_SCRIPT = PROJECT_ROOT / "script" / "aws_download_gvcf.sh"


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://wgs_user:password@localhost:55433/wgs",
)

# Local development remains usable with no API key. For shared/staged/prod
# deployments set VCBENCH_API_KEYS, for example: "admin:change-me".
AUTH_DISABLED = _bool_env("VCBENCH_AUTH_DISABLED", default=False)
API_KEYS = os.getenv("VCBENCH_API_KEYS", "")
INTERNAL_API_KEY = os.getenv("VCBENCH_INTERNAL_API_KEY", "")
AWS_PROFILE = os.getenv("AWS_PROFILE", "vitalite")

MAX_UPLOAD_BYTES = _int_env("VCBENCH_MAX_UPLOAD_BYTES", 20 * 1024 * 1024 * 1024)
MAX_ZIP_MEMBERS = _int_env("VCBENCH_MAX_ZIP_MEMBERS", 5000)
MAX_EXTRACTED_BYTES = _int_env("VCBENCH_MAX_EXTRACTED_BYTES", 100 * 1024 * 1024 * 1024)
