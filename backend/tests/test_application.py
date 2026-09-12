import io
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import comparison
import crud
import main
import models
from database import get_db


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    models.Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db):
    main.app.dependency_overrides[get_db] = lambda: db
    # No live Redis/browser lifecycle is needed in these API tests.
    with TestClient(main.app, raise_server_exceptions=True) as client:
        yield client
    main.app.dependency_overrides.clear()


def receipt():
    return {
        "supermarket": "mercadona",
        "date": "2026-09-01",
        "total": "3.00",
        "receipt_hash": "a" * 64,
        "products": [
            {
                "raw_name": "LECHE",
                "canonical_name": "Leche 1L",
                "quantity": "2",
                "unit_price": "2.00",
                "total_price": "3.00",
                "barcode": "",
            }
        ],
    }


def png():
    out = io.BytesIO()
    Image.new("RGB", (10, 10)).save(out, format="PNG")
    return out.getvalue()


def test_receipt_preserves_discount_and_deduplicates(client, db):
    result = client.post("/api/purchases", json=receipt())
    assert result.status_code == 201, result.text
    assert result.json()["duplicate"] is False
    assert client.post("/api/purchases", json=receipt()).json()["duplicate"] is True
    assert db.query(models.Purchase).count() == 1
    item = db.query(models.PurchaseItem).one()
    assert item.total_price == Decimal("3.00")
    assert item.unit_price == Decimal("2.00")
    # Discounted lines do not enter the undiscounted comparison history.
    assert db.query(models.PriceHistory).count() == 0


def test_delete_purchase_removes_children(client, db):
    purchase_id = client.post("/api/purchases", json=receipt()).json()["purchase_id"]
    assert client.delete(f"/api/purchases/{purchase_id}").status_code == 200
    assert db.query(models.PurchaseItem).count() == 0
    assert client.get(f"/api/purchases/{purchase_id}").status_code == 404


@pytest.mark.parametrize(
    "field,value", [("total", "9.00"), ("date", None), ("supermarket", "unknown")]
)
def test_unreconciled_receipt_is_not_saved(client, db, field, value):
    data = receipt()
    data[field] = value
    assert client.post("/api/purchases", json=data).status_code == 422
    assert db.query(models.Purchase).count() == 0


def test_bad_quantity_is_rejected(client):
    data = receipt()
    data["products"][0]["quantity"] = "-1"
    assert client.post("/api/purchases", json=data).status_code == 422


@pytest.mark.parametrize("price", ["-1", "0", "NaN", "Infinity"])
def test_manual_invalid_price(client, price):
    assert (
        client.post(
            "/api/products/manual",
            json={"name": "Milk", "supermarket": "mercadona", "price": price},
        ).status_code
        == 422
    )


def test_barcode_identity_precedes_name(db):
    first = crud._find_or_create_product(db, "Milk", "4006381333931")
    second = crud._find_or_create_product(db, "Milk", "5901234123457")
    assert first.id != second.id
    assert crud._find_or_create_product(db, "New label", "4006381333931").id == first.id


def test_similar_names_are_not_merged(db):
    a = crud._find_or_create_product(db, "Milk whole 1L")
    b = crud._find_or_create_product(db, "Milk whole 2L")
    assert a.id != b.id


def test_missing_and_unverified_prices_cannot_win():
    rows = [
        {
            "quantity": 1,
            "total_price": "10",
            "prices": {"mercadona": {"price": 2, "comparable": True}},
        },
        {"quantity": 1, "total_price": "10", "prices": {}},
    ]
    assert comparison.calculate_summary(rows)["cheapest_supermarket"] is None
    rows[0]["prices"]["mercadona"]["comparable"] = False
    assert comparison.calculate_summary(rows[:1])["potential_savings"] == 0


def test_decimal_summary_preserves_paid_line_total():
    result = comparison.calculate_summary(
        [
            {
                "quantity": 2,
                "total_price": "3.00",
                "prices": {"mercadona": {"price": "1.20", "comparable": True}},
            }
        ]
    )
    assert result["cheapest_total"] == 2.4
    assert result["potential_savings"] == 0.6


async def test_redis_failure_does_not_stop_search(monkeypatch):
    monkeypatch.setattr(
        comparison.redis_client, "get", AsyncMock(side_effect=ConnectionError)
    )
    monkeypatch.setattr(
        comparison.redis_client, "setex", AsyncMock(side_effect=ConnectionError)
    )
    monkeypatch.setitem(
        comparison.SCRAPERS,
        "mercadona",
        SimpleNamespace(search=AsyncMock(return_value={"name": "Milk", "price": 2})),
    )
    result = await comparison.lookup("mercadona", "Milk")
    assert result["status"] == "candidate"
    assert result["comparable"] is False


async def test_connector_error_and_missing_price_are_distinct(monkeypatch):
    monkeypatch.setattr(comparison.redis_client, "get", AsyncMock(return_value=None))
    monkeypatch.setitem(
        comparison.SCRAPERS,
        "mercadona",
        SimpleNamespace(search=AsyncMock(side_effect=RuntimeError)),
    )
    assert (await comparison.lookup("mercadona", "Milk"))["status"] == "error"
    monkeypatch.setitem(
        comparison.SCRAPERS,
        "mercadona",
        SimpleNamespace(search=AsyncMock(return_value={"price": 0})),
    )
    assert (await comparison.lookup("mercadona", "Milk"))["status"] == "unavailable"


def test_invalid_image_is_rejected(client):
    assert (
        client.post(
            "/api/analyze-ticket",
            files={"file": ("x.jpg", b"not an image", "image/jpeg")},
        ).status_code
        == 422
    )


def test_oversized_image_is_rejected(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_IMAGE_BYTES", 10)
    assert (
        client.post(
            "/api/analyze-ticket", files={"file": ("x.png", png(), "image/png")}
        ).status_code
        == 413
    )


def test_missing_key_does_not_prevent_startup(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert client.get("/api/health").status_code == 200
    assert (
        client.post(
            "/api/analyze-ticket", files={"file": ("x.png", png(), "image/png")}
        ).status_code
        == 503
    )


def test_ocr_is_review_only(client, db, monkeypatch):
    import json

    payload = receipt()
    payload.pop("receipt_hash")
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content=json.dumps(payload)),
            )
        ]
    )
    provider = AsyncMock()
    provider.__aenter__.return_value.chat.completions.create = AsyncMock(
        return_value=response
    )
    monkeypatch.setattr(main, "AsyncOpenAI", lambda **kwargs: provider)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    result = client.post(
        "/api/analyze-ticket", files={"file": ("x.png", png(), "image/png")}
    )
    assert result.status_code == 200, result.text
    assert result.json()["products"][0]["total_price"] == "3.00"
    assert db.query(models.Purchase).count() == 0


def test_analytics_uses_common_identified_basket(db):
    a = crud._find_or_create_product(db, "Milk", "4006381333931")
    b = crud._find_or_create_product(db, "Other", "5901234123457")
    db.add_all(
        [
            models.PriceHistory(product_id=a.id, supermarket="mercadona", price=2),
            models.PriceHistory(product_id=a.id, supermarket="carrefour", price=3),
            models.PriceHistory(product_id=b.id, supermarket="carrefour", price=0.10),
        ]
    )
    db.commit()
    rows = crud.get_cheapest_supermarket(db)
    assert [(r["supermarket"], r["avg_price"], r["data_points"]) for r in rows] == [
        ("mercadona", 2, 1),
        ("carrefour", 3, 1),
    ]
