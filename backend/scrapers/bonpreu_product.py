"""Extract the main product from Bonpreu's public structured data."""

import json
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from urllib.parse import urlsplit

HOST = "www.compraonline.bonpreuesclat.cat"


def product_id(url):
    parts = urlsplit(url)
    segments = parts.path.strip("/").split("/")
    if (
        parts.scheme != "https"
        or parts.hostname != HOST
        or parts.username
        or parts.password
        or parts.port not in (None, 443)
        or len(segments) != 3
        or segments[0] != "products"
        or not segments[-1].isascii()
        or not segments[-1].isdigit()
    ):
        raise ValueError("Invalid Bonpreu product URL")
    return segments[-1]


class StructuredData(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.buffer = []
        self.documents = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.active = dict(attrs).get("type") == "application/ld+json"
            self.buffer = []

    def handle_data(self, data):
        if self.active:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.active:
            try:
                self.documents.append(json.loads("".join(self.buffer)))
            except ValueError:
                pass
            self.active = False


def nodes(value):
    if isinstance(value, list):
        for entry in value:
            yield from nodes(entry)
    elif isinstance(value, dict):
        yield value
        yield from nodes(value.get("@graph", []))


def parse_product(html, url):
    sku = product_id(url)
    parser = StructuredData()
    parser.feed(html)
    matches = [
        item
        for item in nodes(parser.documents)
        if item.get("@type") == "Product" and str(item.get("sku")) == sku
    ]
    if len(matches) != 1:
        raise ValueError("Main Bonpreu product data missing or ambiguous")
    item = matches[0]
    offer = item.get("offers")
    if not isinstance(offer, dict) or offer.get("@type") != "Offer":
        raise ValueError("Bonpreu offer missing")
    if offer.get("availability") in (
        "https://schema.org/OutOfStock",
        "https://schema.org/Discontinued",
    ):
        return None
    if offer.get("availability") != "https://schema.org/InStock":
        raise ValueError("Unknown Bonpreu availability")
    try:
        price = Decimal(str(offer.get("price")))
        if not price.is_finite() or price <= 0 or offer.get("priceCurrency") != "EUR":
            raise ValueError
    except (InvalidOperation, ValueError):
        raise ValueError("Invalid Bonpreu price") from None
    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Bonpreu product name missing")
    size = item.get("size")
    if isinstance(size, str) and size.casefold() not in name.casefold():
        name = f"{name} · {size}"
    image = item.get("image")
    if isinstance(image, list):
        image = image[0] if image else None
    return {
        "name": name.strip(),
        "price": float(price),
        "url": url,
        "image": image if isinstance(image, str) else None,
        "size": size,
        "comparable": False,
    }
