from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
import sys
from pathlib import Path

# Add qc-dashboard root to path
ROOT = Path(__file__).resolve().parent.parent.parent  # qc-dashboard
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.app.api_v1.endpoints import happy_metrics, users, runs, qc_metrics, dash, uploads

# Import the Dash app
from dash_app.app import dash_app

app = FastAPI(
    title="WGS Quality Control Dashboard",
    description="API for managing WGS quality control data and processing",
    version="1.0.0"
)

# CORS setup for development
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # Add other frontend dev URLs as needed
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers with proper prefixes (before mounting Dash)
app.include_router(happy_metrics.router, prefix="/api/v1", tags=["happy-metrics"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(runs.router, prefix="/api/v1", tags=["runs"])
app.include_router(uploads.router, prefix="/api/v1", tags=["uploads"])
app.include_router(qc_metrics.router, prefix="/api/v1", tags=["qc-metrics"])
app.include_router(dash.router, prefix="/api/v1/dash", tags=["dash"])

# Mount the Dash app at the root path
app.mount("/", WSGIMiddleware(dash_app.server))
