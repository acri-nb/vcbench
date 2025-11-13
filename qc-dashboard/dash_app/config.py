# File: qc-dashboard/api/app/dash_app/config.py

import os
from pathlib import Path

# Configuration API
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = os.getenv("API_PORT", "8002")
API_BASE_URL = f"http://{API_HOST}:{API_PORT}/api/v1"

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
print(PROJECT_DIR)
DATA_DIR = PROJECT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
LAB_RUNS_DIR = DATA_DIR / "lab_runs"
DASH_DIR = PROJECT_DIR / "qc_dashboard" / "dash_app"
ASSETS_DIR = DASH_DIR / "assets"

# Types de fichiers et suffixes associés
FILE_TYPES = {
    "Summary":              "summary.csv",
    "Metrics":              "sv_metrics.csv",
    "VC_metrics":           "vc_metrics.csv",
    "CNV_metrics":          "cnv_metrics.csv",
    "ROH_metrics":          "roh_metrics.csv",
    "HeThom":               "vc_hethom_ratio_metrics.csv",
    "Ploidy":               "ploidy_estimation_metrics.csv",
    "bed_coverage":         "bed_coverage_metrics.csv",
    "WGS_contig_mean_cov":  "wgs_contig_mean_cov.csv",
    "mapping_metrics":      "mapping_metrics.csv"
}

# Métriques à typer en int si besoin côté front
INT_METRICS = [
    "True-pos-baseline",
    "True-pos-call",
    "False-pos",
    "False-neg"
]
