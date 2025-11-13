#!/usr/bin/env python3
"""
Initialize the database - create all tables defined in models
"""
import sys
from pathlib import Path

# Add qc-dashboard to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from api.app.database import Base, engine
from api.app import models  # Import models to register them with Base

def init_database():
    """Create all database tables"""
    print("Initializing database...")
    print(f"Database URL: {engine.url}")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("\n✅ Database initialized successfully!")
        print("\nCreated tables:")
        for table in Base.metadata.sorted_tables:
            print(f"  - {table.name}")
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_database()

