from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import Category, Product, ProductVariant


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    with SessionLocal() as session:
        sneakers = Category(name="Sneakers", slug="sneakers", description="Shoes")
        streetwear = Category(name="Streetwear", slug="streetwear", description="Apparel")
        product = Product(
            category=sneakers,
            name="Jordan 1 Retro High Test",
            slug="jordan-1-retro-high-test",
            brand="Jordan",
            description="A seeded sneaker for API tests.",
            image_url="https://example.test/jordan.png",
            lowest_ask_cents=24300,
            total_sold=12,
        )
        variant = ProductVariant(product=product, size="10", color="Black", sku="J1-TEST-10")
        hoodie = Product(
            category=streetwear,
            name="Supreme Test Hoodie",
            slug="supreme-test-hoodie",
            brand="Supreme",
            description="A seeded hoodie for API tests.",
            image_url="https://example.test/hoodie.png",
            lowest_ask_cents=5700,
            total_sold=7,
        )
        session.add_all([sneakers, streetwear, product, variant, hoodie])
        session.commit()
        yield session


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

