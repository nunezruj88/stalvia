from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import anthropic
import base64
import json
import asyncio
import os
import redis.asyncio as aioredis

from scrapers import mercadona, carrefour, bonpreu, elcorteingles, alcampo

app = FastAPI(title="StalvIA API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = aioredis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SUPERMARKETS = ["mercadona", "carrefour", "bonpreu", "elcorteingles", "alcampo"]


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "StalvIA", "supermarkets": SUPERMARKETS}


@app.post("/api/analyze-ticket")
async def analyze_ticket(file: UploadFile = File(...)):
    """
    Receives a receipt image, extracts products via Claude Vision
    and returns a price comparison across all 5 supermarkets.
    """
    image_data = await file.read()
    b64 = base64.standard_b64encode(image_data).decode()

    # 1. OCR with Claude Vision
    response = claude.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": file.content_type,
                        "data": b64
                    }
                },
                {
                    "type": "text",
                    "text": """You are an expert OCR system for Spanish and Catalan supermarket receipts.
Extract all products from this receipt.
Reply ONLY with valid JSON, no markdown or extra text:
{
  "supermarket": "mercadona|carrefour|bonpreu|elcorteingles|alcampo|unknown",
  "date": "YYYY-MM-DD or null",
  "total": 0.00,
  "products": [
    {
      "raw_name": "exact name from receipt",
      "canonical_name": "full normalized product name",
      "quantity": 1,
      "unit_price": 0.00,
      "total_price": 0.00
    }
  ]
}
Normalize names: remove abbreviations, write the full product name."""
                }
            ]
        }]
    )

    try:
        ticket_data = json.loads(response.content[0].text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Could not parse receipt response")

    # 2. Compare prices for each product in parallel across all 5 supermarkets
    products = ticket_data.get("products", [])
    comparison_results = await asyncio.gather(*[
        compare_product(p) for p in products
    ])

    return {
        "supermarket": ticket_data.get("supermarket"),
        "date": ticket_data.get("date"),
        "total_paid": ticket_data.get("total"),
        "products": list(comparison_results),
        "summary": calculate_summary(list(comparison_results))
    }


async def compare_product(product: dict) -> dict:
    """Search for a product across all 5 supermarkets and return the comparison."""
    name = product.get("canonical_name", product.get("raw_name", ""))
    cache_key = f"compare:{name.lower().strip()}"

    # Check Redis cache
    cached = await redis_client.get(cache_key)
    if cached:
        prices = json.loads(cached)
    else:
        # Scrape all 5 supermarkets in parallel
        results = await asyncio.gather(
            mercadona.search(name),
            carrefour.search(name),
            bonpreu.search(name),
            elcorteingles.search(name),
            alcampo.search(name),
            return_exceptions=True
        )

        prices = {
            "mercadona":      results[0] if not isinstance(results[0], Exception) else None,
            "carrefour":      results[1] if not isinstance(results[1], Exception) else None,
            "bonpreu":        results[2] if not isinstance(results[2], Exception) else None,
            "elcorteingles":  results[3] if not isinstance(results[3], Exception) else None,
            "alcampo":        results[4] if not isinstance(results[4], Exception) else None,
        }

        # Cache for 4 hours
        await redis_client.setex(cache_key, 14400, json.dumps(prices))

    # Find the best price
    available_prices = {
        k: v["price"] for k, v in prices.items()
        if v and v.get("price") is not None
    }
    best_super = min(available_prices, key=available_prices.get) if available_prices else None

    return {
        "raw_name": product.get("raw_name"),
        "canonical_name": product.get("canonical_name"),
        "quantity": product.get("quantity", 1),
        "price_paid": product.get("unit_price"),
        "prices": prices,
        "best_supermarket": best_super,
        "best_price": available_prices.get(best_super) if best_super else None,
    }


def calculate_summary(products: list) -> dict:
    """Calculate total per supermarket and potential savings."""
    totals = {s: 0.0 for s in SUPERMARKETS}

    for p in products:
        qty = p.get("quantity", 1)
        for super_name in SUPERMARKETS:
            price_info = p.get("prices", {}).get(super_name)
            if price_info and price_info.get("price"):
                totals[super_name] += price_info["price"] * qty

    total_paid = sum(
        p.get("price_paid", 0) * p.get("quantity", 1)
        for p in products
        if p.get("price_paid")
    )

    valid_totals = {k: v for k, v in totals.items() if v > 0}
    cheapest_super = min(valid_totals, key=valid_totals.get) if valid_totals else None

    return {
        "total_paid": round(total_paid, 2),
        "totals_by_super": {k: round(v, 2) for k, v in totals.items()},
        "cheapest_supermarket": cheapest_super,
        "cheapest_total": round(valid_totals[cheapest_super], 2) if cheapest_super else None,
        "potential_savings": round(total_paid - valid_totals[cheapest_super], 2)
        if cheapest_super and total_paid > 0 else 0,
    }


@app.get("/api/products")
async def get_products():
    """Return the product catalogue."""
    # TODO: implement with SQLAlchemy
    return {"products": []}


@app.get("/api/purchases")
async def get_purchases():
    """Return purchase history."""
    # TODO: implement with SQLAlchemy
    return {"purchases": []}


@app.get("/api/price-history/{product_id}")
async def get_price_history(product_id: int):
    """Return price evolution for a product."""
    # TODO: implement with SQLAlchemy
    return {"product_id": product_id, "history": []}
