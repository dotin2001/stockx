from collections.abc import Generator

from sqlalchemy import create_engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

database_url = settings.database_url.get_secret_value()
connect_args = (
    {"connect_timeout": max(1, int(settings.database_connect_timeout_seconds))}
    if make_url(database_url).get_backend_name() == "postgresql"
    else {}
)
engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
