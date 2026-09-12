import asyncio
import hashlib
import io
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

import crud
import models
import schemas
from ai import (
    AIConfigurationError,
    AIProviderError,
    AIResponseError,
    configuration_status,
    extract_receipt,
)
from comparison import close_resources, compare_product
from database import engine, get_db
from receipt import ManualProductInput, ReceiptLine, ReviewedReceipt
from settings import MAX_IMAGE_BYTES

ocr_slots = asyncio.Semaphore(2)


@asynccontextmanager
async def lifespan(app):
    yield
    await close_resources()
    engine.dispose()


app = FastAPI(title="StalvIA API", version="0.2.0", lifespan=lifespan)
origins = [v.strip() for v in os.getenv("CORS_ORIGINS", "").split(",") if v.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(
        status_code=409,
        content={
            "detail": "El registro ya existe o entra en conflicto con datos guardados."
        },
    )


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1 FROM purchases LIMIT 1"))
    except Exception:
        raise HTTPException(503, "Base de datos o migraciones no disponibles") from None
    ai_status = configuration_status()
    return {
        "status": "ok",
        "service": "StalvIA",
        "ocr_configured": ai_status["configured"],
        "ai": ai_status,
    }


def image_payload(data):
    try:
        with Image.open(io.BytesIO(data)) as picture:
            if (
                picture.format not in ("JPEG", "PNG", "WEBP")
                or picture.width * picture.height > 20000000
            ):
                raise ValueError("Unsupported image")
            mime = Image.MIME[picture.format]
            picture.verify()
            return mime
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(
            422, "Sube una imagen JPEG, PNG o WebP válida de hasta 20 megapíxeles"
        ) from None


@app.post("/api/analyze-ticket")
async def analyze_ticket(file: UploadFile = File(...)):
    # Extraction never writes a purchase; the user reviews it first.
    data = await file.read(MAX_IMAGE_BYTES + 1)
    await file.close()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "La imagen supera 8 MB")
    mime = await run_in_threadpool(image_payload, data)
    try:
        async with ocr_slots:
            receipt = await extract_receipt(data, mime)
    except AIConfigurationError as exc:
        raise HTTPException(503, str(exc)) from None
    except AIProviderError as exc:
        raise HTTPException(502, str(exc)) from None
    except AIResponseError as exc:
        raise HTTPException(422, str(exc)) from None
    return {
        **receipt.model_dump(mode="json"),
        "receipt_hash": hashlib.sha256(data).hexdigest(),
        "warnings": receipt.warnings(),
    }


@app.post("/api/purchases", status_code=201)
def save_reviewed_ticket(receipt: ReviewedReceipt, db: Session = Depends(get_db)):
    existing = (
        db.query(models.Purchase).filter_by(receipt_hash=receipt.receipt_hash).first()
    )
    if existing:
        return {"purchase_id": existing.id, "duplicate": True}
    products = [
        {**p.model_dump(), "price_paid": p.unit_price, "prices": {}}
        for p in receipt.products
    ]
    purchase = crud.save_purchase(
        db,
        receipt.supermarket,
        receipt.date.isoformat(),
        receipt.total,
        products,
        receipt.receipt_hash,
    )
    return {"purchase_id": purchase.id, "duplicate": False}


@app.post("/api/compare-product")
async def compare_reviewed_product(product: ReceiptLine):
    # One bounded request per product allows the UI to report progress and retry.
    try:
        return await asyncio.wait_for(
            compare_product(product.model_dump(mode="json")), timeout=105
        )
    except TimeoutError:
        raise HTTPException(
            504,
            "La comparación tardó demasiado. Puedes reintentarlo; el ticket sigue guardado.",
        ) from None


# ─── Purchases ────────────────────────────────────────────────────────────────


@app.get("/api/purchases", response_model=list[schemas.PurchaseSummary])
def get_purchases(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
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


@app.get("/api/catalog")
def get_catalog(
    search: str = Query("", max_length=250),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return crud.get_catalog(db, search=search, skip=skip, limit=limit)


# ─── Products ─────────────────────────────────────────────────────────────────


@app.get("/api/products", response_model=list[schemas.ProductSummary])
def get_products(
    search: str = "",
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
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
    days: int = Query(180, ge=1, le=3650),
    db: Session = Depends(get_db),
):
    """
    Return price evolution for a product.
    Optional filters: supermarket name, number of days back.
    """
    return crud.get_price_history(db, product_id, supermarket=supermarket, days=days)


# ─── Manual product entry ─────────────────────────────────────────────────────


@app.post("/api/products/manual")
def add_manual_product(data: ManualProductInput, db: Session = Depends(get_db)):
    """Manually register a product price for a specific supermarket."""
    return crud.save_manual_product(
        db=db,
        name=data.name,
        supermarket=data.supermarket,
        price=data.price,
        barcode=data.barcode or None,
        category=data.category or None,
    )


@app.get("/api/analytics/cheapest-super", response_model=list[schemas.SupermarketAvg])
def get_cheapest_super(
    days: int = Query(30, ge=1, le=3650), db: Session = Depends(get_db)
):
    """Return average price per supermarket over the last N days."""
    return crud.get_cheapest_supermarket(db, days=days)


@app.get("/api/analytics/spending", response_model=list[schemas.SpendingByMonth])
def get_spending(db: Session = Depends(get_db)):
    """Return monthly spending totals."""
    return crud.get_monthly_spending(db)
