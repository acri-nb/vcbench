from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database connection URL for PostgreSQL docker container
# Note: Port 5433 is used to avoid conflicts with other PostgreSQL instances
DATABASE_URL = 'postgresql+psycopg2://wgs_user:password@localhost:5433/wgs'

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a declarative base class for model definitions
Base = declarative_base()

# Create a ORM session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to get the database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
