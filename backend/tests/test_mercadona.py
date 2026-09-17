import pytest

from scrapers.mercadona import parse_result, postal_code


def product(price="5.76", pack=True):
    return {
        "hits": [
            {
                "id": "10379",
                "display_name": "Leche entera Hacendado",
                "packaging": "Brik",
                "price_instructions": {
                    "unit_price": price,
                    "unit_size": 6.0 if pack else 1.0,
                    "size_format": "l",
                    "is_pack": pack,
                    "pack_size": 1.0,
                    "total_units": 6 if pack else 1,
                },
            }
        ]
    }


def test_pack_price_is_not_unit_price():
    result = parse_result(product(), "08759")
    assert result["price"] == 5.76
    assert result["name"].endswith("6 x 1 l")
    assert result["postal_code"] == "08759"
    assert result["comparable"] is False
    single = parse_result(product("0.96", False), "08759")
    assert single["name"].endswith("Brik 1 l")
    assert single["price"] == 0.96


def test_empty_results_are_distinct_from_invalid_response():
    assert parse_result({"hits": []}, "08759") is None
    with pytest.raises(ValueError):
        parse_result({"error": "blocked"}, "08759")


@pytest.mark.parametrize("price", ["NaN", "Infinity", "0", "-1"])
def test_invalid_price_is_rejected(price):
    with pytest.raises(ValueError):
        parse_result(product(price), "08759")


def test_postcode_keeps_leading_zero(monkeypatch):
    monkeypatch.setenv("MERCADONA_POSTAL_CODE", "08759")
    assert postal_code() == "08759"
    monkeypatch.setenv("MERCADONA_POSTAL_CODE", "8759")
    with pytest.raises(ValueError):
        postal_code()
