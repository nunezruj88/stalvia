import json
from pathlib import Path

import pytest

from scrapers.bonpreu_product import parse_product, product_id

URL = "https://www.compraonline.bonpreuesclat.cat/products/viladrau-garrafa-5l/16101"


@pytest.fixture
def product():
    return json.loads(
        (Path(__file__).parent / "fixtures/bonpreu_viladrau.json").read_text(
            encoding="utf-8"
        )
    )


def html(data):
    return '<script type="application/ld+json">' + json.dumps(data) + "</script>"


def test_saved_product_and_recommendations(product):
    recommendation = dict(product, sku="14928", name="Other water")
    result = parse_product(
        html(recommendation) + html(product) + "<span>0,38 €/L</span>", URL
    )
    assert result["price"] == 1.89
    assert result["size"] == "5L"
    assert result["name"] == "VILADRAU Aigua mineral natural dèbil garrafa 5L"
    assert result["comparable"] is False


def test_graph_and_missing_product(product):
    assert parse_product(html({"@graph": [product]}), URL)["price"] == 1.89
    with pytest.raises(ValueError):
        parse_product("<h1>Access denied</h1>", URL)
    with pytest.raises(ValueError):
        parse_product(html(dict(product, sku="14928")), URL)


@pytest.mark.parametrize("price", ["NaN", "Infinity", "-1", "0", "bad"])
def test_invalid_prices(product, price):
    product["offers"]["price"] = price
    with pytest.raises(ValueError):
        parse_product(html(product), URL)


def test_unavailable_and_currency(product):
    product["offers"]["priceCurrency"] = "USD"
    with pytest.raises(ValueError):
        parse_product(html(product), URL)
    product["offers"]["availability"] = "https://schema.org/OutOfStock"
    assert parse_product(html(product), URL) is None


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/products/x/1",
        "https://example.com/products/x/1",
        "https://www.compraonline.bonpreuesclat.cat@evil.test/products/x/1",
        "https://www.compraonline.bonpreuesclat.cat/search?q=water",
    ],
)
def test_product_url_validation(url):
    with pytest.raises(ValueError):
        product_id(url)
