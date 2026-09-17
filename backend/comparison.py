import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import redis.asyncio as aioredis

from scrapers import alcampo, bonpreu, carrefour, elcorteingles, mercadona
from scrapers.browser import close_browser
from settings import SUPERMARKETS

logger = logging.getLogger(__name__)
redis_client = aioredis.from_url(
    os.getenv("REDIS_URL", "redis://redis:6379"),
    socket_connect_timeout=1,
    socket_timeout=1,
)
slots = asyncio.Semaphore(max(1, min(4, int(os.getenv("SCRAPER_CONCURRENCY", "2")))))
SCRAPERS = dict(
    zip(SUPERMARKETS, (mercadona, carrefour, bonpreu, elcorteingles, alcampo))
)


def positive_price(value):
    try:
        value = Decimal(str(value))
        return value if value.is_finite() and value > 0 else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def calculate_summary(products):
    totals, coverage = {}, {}
    for store in SUPERMARKETS:
        matches = [(p, p.get("prices", {}).get(store)) for p in products]
        matches = [
            (p, offer)
            for p, offer in matches
            if offer and offer.get("comparable") and positive_price(offer.get("price"))
        ]
        coverage[store] = len(matches)
        # Partial baskets have no total and cannot win.
        totals[store] = (
            float(
                sum(
                    positive_price(o["price"]) * Decimal(str(p["quantity"]))
                    for p, o in matches
                ).quantize(Decimal("0.01"))
            )
            if products and len(matches) == len(products)
            else None
        )
    paid = sum(Decimal(str(p["total_price"])) for p in products)
    complete = {s: p for s, p in totals.items() if p is not None}
    cheapest = min(complete, key=complete.get) if complete else None
    return {
        "total_paid": float(paid),
        "totals_by_super": totals,
        "coverage": coverage,
        "product_count": len(products),
        "cheapest_supermarket": cheapest,
        "cheapest_total": complete.get(cheapest),
        "potential_savings": float(
            max(Decimal(0), paid - Decimal(str(complete[cheapest]))).quantize(
                Decimal("0.01")
            )
        )
        if cheapest
        else 0,
    }


async def lookup(store, name):
    key = (
        f"offer:v3:{store}:{os.getenv('MERCADONA_POSTAL_CODE', '08759')}:{name.casefold()}"
    )
    try:
        cached = await redis_client.get(key)
        if cached:
            result = json.loads(cached)
            if isinstance(result, dict) and positive_price(result.get("price")):
                return result
    except Exception:
        logger.warning("Price cache unavailable; querying connector")
    try:
        async with slots:
            result = await asyncio.wait_for(SCRAPERS[store].search(name), timeout=28)
        if not result or not positive_price(result.get("price")):
            return {"status": "unavailable", "price": None, "comparable": False}
        result.update(
            status="candidate",
            comparable=False,
            observed_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            await redis_client.setex(key, 14400, json.dumps(result))
        except Exception:
            logger.warning("Could not cache price")
        return result
    except Exception:
        logger.exception("Connector failed: %s", store)
        return {"status": "error", "price": None, "comparable": False}


async def compare_product(product):
    name = product["canonical_name"]
    results = await asyncio.gather(*(lookup(s, name) for s in SUPERMARKETS))
    # A search result alone is not evidence of product/pack equivalence.
    return {
        **product,
        "price_paid": product["unit_price"],
        "prices": dict(zip(SUPERMARKETS, results)),
    }


async def close_resources():
    await redis_client.aclose()
    await close_browser()
