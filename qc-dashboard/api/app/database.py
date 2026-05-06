from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from api.app.settings import DATABASE_URL

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

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
