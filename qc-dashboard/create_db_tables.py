#!/usr/bin/env python3
"""
Create database tables for VCBench
Run this script from the qc-dashboard directory
Usage: python create_db_tables.py
"""
import sys
import os
from pathlib import Path

def main():
    """Main function to create database tables"""
    print("🔧 Setting up database tables for VCBench...")

    # Verify we're in the right directory
    current_dir = Path.cwd()
    if not (current_dir / "api" / "app" / "models.py").exists():
        print(f"❌ Error: Please run this script from the qc-dashboard directory")
        print(f"Current directory: {current_dir}")
        print(f"Expected: .../qc-dashboard/")
        return False

    print(f"📁 Working directory: {current_dir}")

    try:
        # Import modules (should work when run from qc-dashboard directory)
        from api.app.models import Base
        from api.app.database import engine
        print("✅ Successfully imported database modules")

        # Test database connection
        print("🔍 Testing database connection...")
        from sqlalchemy import text
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1;"))
            print("✅ Database connection successful")

        # Create tables
        print("📋 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")

        # List created tables
        print("\n📊 Tables created:")
        table_names = [table.name for table in Base.metadata.sorted_tables]
        for table_name in table_names:
            print(f"  • {table_name}")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Python path: {sys.path}")
        print("\n🔍 Troubleshooting:")
        print("1. Make sure you're in the qc-dashboard directory")
        print("2. Check if api/app/models.py exists")
        print("3. Verify conda environment: conda activate bioinfo")
        return False

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        print("\n🔍 Troubleshooting:")
        print("1. Make sure Docker services are running: docker compose ps")
        print("2. Check database connection: docker compose logs db")
        print("3. Verify database URL in api/app/database.py")
        return False

    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Database setup complete!")
        print("Next steps:")
        print("  1. Start the API server: ./start_app.sh")
        print("  2. Access API docs at: http://localhost:8000/docs")
    else:
        print("\n❌ Database setup failed")
        sys.exit(1)
