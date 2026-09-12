"""Run against a migrated, disposable PostgreSQL database in CI."""

import os

import pytest
from sqlalchemy import create_engine, inspect, text


@pytest.mark.skipif(
    not os.getenv("TEST_POSTGRES_URL"),
    reason="PostgreSQL integration database not configured",
)
def test_migrated_postgres_schema():
    engine = create_engine(os.environ["TEST_POSTGRES_URL"])
    inspector = inspect(engine)
    assert {"purchases", "purchase_items", "products", "price_history"} <= set(
        inspector.get_table_names()
    )
    assert "receipt_hash" in {c["name"] for c in inspector.get_columns("purchases")}
    assert "source" in {c["name"] for c in inspector.get_columns("price_history")}
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT extname FROM pg_extension WHERE extname='pg_trgm'")
            )
            == "pg_trgm"
        )
        indexes = (
            connection.execute(
                text("SELECT indexname FROM pg_indexes WHERE schemaname='public'")
            )
            .scalars()
            .all()
        )
        assert "idx_products_canonical_trgm" in indexes
        assert "idx_product_aliases_trgm" in indexes
    engine.dispose()
