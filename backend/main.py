from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from openai import OpenAI
import base64
import json
import asyncio
import os
import redis.asyncio as aioredis

from database import get_db
from scrapers import mercadona, carrefour, bonpreu, elcorteingles, alcampo
import crud
import schemas

app = FastAPI(title="StalvIA API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = aioredis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))
kimi = OpenAI(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    base_url="https://api.openai.com/v1",
)

SUPERMARKETS = ["mercadona", "carrefour", "bonpreu", "elcorteingles", "alcampo"]


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "StalvIA", "supermarkets": SUPERMARKETS}


# ─── Ticket analysis ──────────────────────────────────────────────────────────

@app.post("/api/analyze-ticket", response_model=schemas.TicketResponse)
async def analyze_ticket(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Receives a receipt image, extracts products via Claude Vision,
    compares prices across all 5 supermarkets, and saves to the database.
    """
    image_data = await file.read()
    b64 = base64.standard_b64encode(image_data).decode()

    # 1. OCR with Kimi Vision
    response = kimi.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{file.content_type};base64,{b64}"
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
        }],
        max_tokens=2000,
    )

    raw_text = response.choices[0].message.content
    # Strip markdown fences if model wraps response
    raw_text = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        ticket_data = json.loads(raw_text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Could not parse receipt response")

    # 2. Compare prices across all 5 supermarkets in parallel
    raw_products = ticket_data.get("products", [])
    comparison_results = await asyncio.gather(*[
        compare_product(p) for p in raw_products
    ])
    comparison_results = list(comparison_results)

    # 3. Save to database
    purchase = crud.save_purchase(
        db=db,
        supermarket=ticket_data.get("supermarket", "unknown"),
        purchase_date=ticket_data.get("date"),
        total_amount=ticket_data.get("total"),
        products=comparison_results,
    )

    return {
        "purchase_id": purchase.id,
        "supermarket": ticket_data.get("supermarket"),
        "date": ticket_data.get("date"),
        "total_paid": ticket_data.get("total"),
        "products": comparison_results,
        "summary": calculate_summary(comparison_results),
    }


async def compare_product(product: dict) -> dict:
    """Search for a product across all 5 supermarkets and return the comparison."""
    name = product.get("canonical_name", product.get("raw_name", ""))
    cache_key = f"compare:{name.lower().strip()}"

    cached = await redis_client.get(cache_key)
    if cached:
        prices = json.loads(cached)
    else:
        results = await asyncio.gather(
            mercadona.search(name),
            carrefour.search(name),
            bonpreu.search(name),
            elcorteingles.search(name),
            alcampo.search(name),
            return_exceptions=True
        )
        prices = {
            "mercadona":     results[0] if not isinstance(results[0], Exception) else None,
            "carrefour":     results[1] if not isinstance(results[1], Exception) else None,
            "bonpreu":       results[2] if not isinstance(results[2], Exception) else None,
            "elcorteingles": results[3] if not isinstance(results[3], Exception) else None,
            "alcampo":       results[4] if not isinstance(results[4], Exception) else None,
        }
        await redis_client.setex(cache_key, 14400, json.dumps(prices))

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
        for s in SUPERMARKETS:
            info = p.get("prices", {}).get(s)
            if info and info.get("price"):
                totals[s] += info["price"] * qty

    total_paid = sum(
        (p.get("price_paid") or 0) * p.get("quantity", 1)
        for p in products
    )
    valid_totals = {k: v for k, v in totals.items() if v > 0}
    cheapest = min(valid_totals, key=valid_totals.get) if valid_totals else None

    return {
        "total_paid": round(total_paid, 2),
        "totals_by_super": {k: round(v, 2) for k, v in totals.items()},
        "cheapest_supermarket": cheapest,
        "cheapest_total": round(valid_totals[cheapest], 2) if cheapest else None,
        "potential_savings": round(total_paid - valid_totals[cheapest], 2)
        if cheapest and total_paid > 0 else 0,
    }


# ─── Purchases ────────────────────────────────────────────────────────────────

@app.get("/api/purchases", response_model=list[schemas.PurchaseSummary])
def get_purchases(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Return paginated purchase history."""
    return crud.get_purchases(db, skip=skip, limit=limit)


@app.get("/api/purchases/{purchase_id}", response_model=schemas.PurchaseDetail)
def get_purchase(purchase_id: int, db: Session = Depends(get_db)):
    """Return a single purchase with all its items."""
    purchase = crud.get_purchase(db, purchase_id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return purchase


@app.delete("/api/purchases/{purchase_id}")
def delete_purchase(purchase_id: int, db: Session = Depends(get_db)):
    """Delete a purchase and its items."""
    ok = crud.delete_purchase(db, purchase_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return {"ok": True}


# ─── Products ─────────────────────────────────────────────────────────────────

@app.get("/api/products", response_model=list[schemas.ProductSummary])
def get_products(search: str = "", skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Return product catalogue, optionally filtered by name."""
    return crud.get_products(db, search=search, skip=skip, limit=limit)


@app.get("/api/products/{product_id}", response_model=schemas.ProductDetail)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Return a single product with its aliases."""
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ─── Price history ────────────────────────────────────────────────────────────

@app.get("/api/price-history/{product_id}", response_model=list[schemas.PricePoint])
def get_price_history(
    product_id: int,
    supermarket: str = "",
    days: int = 180,
    db: Session = Depends(get_db)
):
    """
    Return price evolution for a product.
    Optional filters: supermarket name, number of days back.
    """
    return crud.get_price_history(db, product_id, supermarket=supermarket, days=days)


@app.get("/api/analytics/cheapest-super", response_model=list[schemas.SupermarketAvg])
def get_cheapest_super(days: int = 30, db: Session = Depends(get_db)):
    """Return average price per supermarket over the last N days."""
    return crud.get_cheapest_supermarket(db, days=days)


@app.get("/api/analytics/spending", response_model=list[schemas.SpendingByMonth])
def get_spending(db: Session = Depends(get_db)):
    """Return monthly spending totals."""
    return crud.get_monthly_spending(db)
