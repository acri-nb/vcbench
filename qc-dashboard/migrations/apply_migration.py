#!/usr/bin/env python3
"""
Apply database migrations for the VCBench QC Dashboard
"""
import sys
from pathlib import Path

# Add qc-dashboard to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.app.database import engine
from sqlalchemy import text

def apply_migration(migration_file: Path):
    """Apply a single migration SQL file"""
    print(f"Applying migration: {migration_file.name}")
    
    try:
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        with engine.connect() as conn:
            # Execute the SQL
            conn.execute(text(sql))
            conn.commit()
        
        print(f"✅ Migration {migration_file.name} applied successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error applying migration {migration_file.name}: {e}")
        return False

def main():
    """Apply all pending migrations"""
    migrations_dir = Path(__file__).parent
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        print("No migration files found")
        return
    
    print(f"Found {len(migration_files)} migration file(s)\n")
    
    success_count = 0
    for migration_file in migration_files:
        if apply_migration(migration_file):
            success_count += 1
        print()
    
    print(f"Migration summary: {success_count}/{len(migration_files)} successful")

if __name__ == "__main__":
    main()

