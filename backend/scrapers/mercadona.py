"""Read the public shop's current search response without embedding API keys."""

import math
import os
import re
from urllib.parse import parse_qs, urlsplit

from .browser import page_context


def postal_code():
    value = os.getenv("MERCADONA_POSTAL_CODE", "08759").strip()
    if not re.fullmatch(r"[0-9]{5}", value):
        raise ValueError("MERCADONA_POSTAL_CODE must contain five digits")
    return value


def parse_result(data, postcode):
    if not isinstance(data, dict) or not isinstance(data.get("hits"), list):
        raise ValueError("Unexpected Mercadona search response")
    if not data["hits"]:
        return None
    item = data["hits"][0]
    prices = item["price_instructions"]
    price = float(prices["unit_price"])
    if not math.isfinite(price) or price <= 0 or not item.get("display_name"):
        raise ValueError("Invalid Mercadona product")
    size = prices.get("unit_size")
    unit = prices.get("size_format", "")
    count = prices.get("total_units")
    pack_size = prices.get("pack_size")
    if prices.get("is_pack") and count and pack_size:
        presentation = f"{count} x {pack_size:g} {unit}"
    elif size:
        presentation = f"{item.get('packaging') or 'Unidad'} {size:g} {unit}"
    else:
        presentation = item.get("packaging") or ""
    return {
        "name": " · ".join(filter(None, [item["display_name"], presentation])),
        "price": price,
        "unit_size": size,
        "unit_name": unit,
        "image": item.get("thumbnail"),
        "url": f"https://tienda.mercadona.es/product/{int(item['id'])}",
        "in_promotion": bool(prices.get("price_decreased")),
        "postal_code": postcode,
        "comparable": False,
    }


async def search(query: str) -> dict | None:
    postcode = postal_code()
    query = query.strip()
    if not query:
        raise ValueError("Empty search")
    async with page_context() as page:
        response = await page.goto(
            "https://tienda.mercadona.es/", wait_until="domcontentloaded", timeout=15000
        )
        if response is None or response.status >= 400:
            raise RuntimeError("Mercadona shop unavailable")
        await page.locator('input[name="postalCode"]').fill(postcode, timeout=8000)

        def is_zone(response):
            url = urlsplit(response.url)
            return (
                url.hostname == "tienda.mercadona.es"
                and url.path == "/api/home/"
                and parse_qs(url.query).get("postal_code") == [postcode]
            )

        async with page.expect_response(is_zone, timeout=8000) as zone:
            await page.get_by_role("button", name="Continuar", exact=True).click()
        if (await zone.value).status != 200:
            raise RuntimeError("Mercadona postal code unavailable")
        reject = page.get_by_role("button", name="Rechazar", exact=True)
        if await reject.is_visible():
            await reject.click()

        def is_search(response):
            url = urlsplit(response.url)
            if not (url.hostname or "").endswith(".algolia.net"):
                return False
            if not url.path.endswith("/query"):
                return False
            payload = response.request.post_data_json
            return isinstance(payload, dict) and payload.get("query") == query

        async with page.expect_response(is_search, timeout=8000) as result:
            box = page.locator('input[name="search"]')
            await box.fill(query)
            await box.press("Enter")
        response = await result.value
        if response.status != 200:
            raise RuntimeError("Mercadona search unavailable")
        return parse_result(await response.json(), postcode)
