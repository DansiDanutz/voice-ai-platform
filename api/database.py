"""Database connection and session management."""
import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker
from .models import Base


def build_database_url():
    """Build a database URL without interpolating raw credentials into text."""
    host = os.getenv("DB_HOST")
    if host:
        password = os.getenv("POSTGRES_PASSWORD")
        if not password:
            raise RuntimeError("POSTGRES_PASSWORD is required when DB_HOST is set")

        return URL.create(
            drivername="postgresql+psycopg2",
            username=os.getenv("POSTGRES_USER", "voice_ai"),
            password=password,
            host=host,
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "voice_ai"),
        )

    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        return make_url(configured_url)

    return make_url("sqlite:///./voice_ai.db")


DATABASE_URL = build_database_url()

# Support both PostgreSQL and SQLite
if DATABASE_URL.get_backend_name() == "sqlite":
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
