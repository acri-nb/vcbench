#!/usr/bin/env python3
"""
Apply database migrations for VCBench.
Run this script from the qc-dashboard directory:
    python create_db_tables.py
"""
import os
import sys
from pathlib import Path


def main() -> bool:
    current_dir = Path.cwd()
    if not (current_dir / "alembic.ini").exists():
        print("Error: please run this script from the qc-dashboard directory.")
        print(f"Current directory: {current_dir}")
        return False

    try:
        from alembic import command
        from alembic.config import Config
        from api.app.settings import DATABASE_URL
    except ImportError as e:
        print(f"Import error: {e}")
        print("Install dependencies first: pip install -r ../requirements.txt")
        return False

    config = Config(str(current_dir / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

    try:
        print("Applying database migrations...")
        command.upgrade(config, "head")
        print("Database schema is up to date.")
        return True
    except Exception as e:
        print(f"Migration failed: {e}")
        print("Check DATABASE_URL and make sure PostgreSQL is running.")
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
