from datetime import datetime

from test_application import client as client_fixture
from test_application import db as db_fixture

import models

client = client_fixture
db = db_fixture


def test_catalog_lists_latest_price_per_store_and_barcode_search(client, db):
    product = models.Product(canonical_name="Leche entera 1L", barcode="4006381333931")
    db.add(product)
    db.flush()
    db.add_all(
        [
            models.PriceHistory(
                product_id=product.id,
                supermarket="mercadona",
                price=1.1,
                scraped_at=datetime(2026, 1, 1),
                source="manual",
            ),
            models.PriceHistory(
                product_id=product.id,
                supermarket="mercadona",
                price=1.3,
                scraped_at=datetime(2026, 2, 1),
                source="receipt",
            ),
            models.PriceHistory(
                product_id=product.id,
                supermarket="carrefour",
                price=1.2,
                scraped_at=datetime(2026, 1, 1),
                source="manual",
            ),
        ]
    )
    db.commit()
    response = client.get("/api/catalog?search=4006381333931")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    row = data["products"][0]
    assert row["barcode"] == product.barcode
    assert row["latest_prices"]["mercadona"]["price"] == 1.3
    assert row["latest_prices"]["mercadona"]["source"] == "receipt"
    assert row["latest_prices"]["carrefour"]["price"] == 1.2


def test_catalog_pagination_no_prices_and_literal_search(client, db):
    db.add_all(
        [
            models.Product(canonical_name="A 100%"),
            models.Product(canonical_name="B"),
            models.Product(canonical_name="C"),
        ]
    )
    db.commit()
    data = client.get("/api/catalog?skip=1&limit=1").json()
    assert data["total"] == 3
    assert data["products"][0]["canonical_name"] == "B"
    assert data["products"][0]["latest_prices"] == {}
    data = client.get("/api/catalog", params={"search": "%"}).json()
    assert data["total"] == 1
    assert data["products"][0]["canonical_name"] == "A 100%"
    assert client.get("/api/catalog?limit=0").status_code == 422
    assert client.get("/api/catalog?skip=-1").status_code == 422


def test_manual_creation_is_immediately_visible_in_catalog(client):
    response = client.post(
        "/api/products/manual",
        json={
            "name": "Leche 1L",
            "barcode": "4006381333931",
            "supermarket": "bonpreu",
            "price": "1.50",
            "category": "dairy",
        },
    )
    assert response.status_code == 200
    data = client.get("/api/catalog?search=Leche").json()
    assert data["products"][0]["id"] == response.json()["product_id"]
    assert data["products"][0]["category"] == "dairy"
    assert data["products"][0]["latest_prices"]["bonpreu"]["price"] == 1.5
