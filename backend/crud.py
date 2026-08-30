from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from datetime import datetime, timedelta
from typing import Optional
import models


# ─── Purchases ────────────────────────────────────────────────────────────────

def save_purchase(
    db: Session,
    supermarket: str,
    purchase_date: Optional[str],
    total_amount: Optional[float],
    products: list[dict],
) -> models.Purchase:
    """
    Save a complete purchase with all its items and price history.
    Creates or reuses products and aliases as needed.
    """
    # Resolve or create the store
    store = db.query(models.Store).filter_by(supermarket=supermarket).first()
    if not store and supermarket not in ("unknown", None):
        store = models.Store(
            supermarket=supermarket,
            name=supermarket.capitalize(),
        )
        db.add(store)
        db.flush()

    # Parse date
    parsed_date = datetime.utcnow()
    if purchase_date:
        try:
            parsed_date = datetime.strptime(purchase_date, "%Y-%m-%d")
        except ValueError:
            pass

    purchase = models.Purchase(
        store_id=store.id if store else None,
        purchase_date=parsed_date,
        total_amount=total_amount,
    )
    db.add(purchase)
    db.flush()

    for p in products:
        # Find or create the canonical product
        product = _find_or_create_product(db, p.get("canonical_name") or p.get("raw_name"))

        # Save raw name as OCR alias if new
        if p.get("raw_name") and p["raw_name"] != product.canonical_name:
            _ensure_alias(db, product.id, p["raw_name"], supermarket, source="ocr")

        # Save purchase item
        unit_price = float(p.get("price_paid") or 0)
        quantity = float(p.get("quantity") or 1)
        item = models.PurchaseItem(
            purchase_id=purchase.id,
            product_id=product.id,
            raw_name=p.get("raw_name", ""),
            quantity=quantity,
            unit_price=unit_price,
            total_price=round(unit_price * quantity, 2),
        )
        db.add(item)

        # Save scraped prices to price_history
        for super_name, price_data in (p.get("prices") or {}).items():
            if price_data and price_data.get("price") is not None:
                # Avoid duplicate entries for today
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                existing = db.query(models.PriceHistory).filter(
                    models.PriceHistory.product_id == product.id,
                    models.PriceHistory.supermarket == super_name,
                    models.PriceHistory.scraped_at >= today_start,
                ).first()
                if not existing:
                    db.add(models.PriceHistory(
                        product_id=product.id,
                        store_id=store.id if store and store.supermarket == super_name else None,
                        supermarket=super_name,
                        price=price_data["price"],
                        in_promotion=price_data.get("in_promotion", False),
                    ))

    db.commit()
    db.refresh(purchase)
    return purchase


def _find_or_create_product(db: Session, canonical_name: str) -> models.Product:
    """Find a product by canonical name (exact or fuzzy via pg_trgm), or create it."""
    if not canonical_name:
        canonical_name = "Unknown product"

    # Exact match first
    product = db.query(models.Product).filter(
        func.lower(models.Product.canonical_name) == canonical_name.lower()
    ).first()
    if product:
        return product

    # Fuzzy match via pg_trgm (similarity > 0.6)
    product = db.query(models.Product).filter(
        text("similarity(canonical_name, :name) > 0.6").bindparams(name=canonical_name)
    ).order_by(
        text("similarity(canonical_name, :name) DESC").bindparams(name=canonical_name)
    ).first()
    if product:
        return product

    # Also check aliases
    alias = db.query(models.ProductAlias).filter(
        func.lower(models.ProductAlias.alias) == canonical_name.lower()
    ).first()
    if alias:
        return alias.product

    # Create new product
    product = models.Product(canonical_name=canonical_name)
    db.add(product)
    db.flush()
    return product


def _ensure_alias(
    db: Session,
    product_id: int,
    alias: str,
    supermarket: Optional[str],
    source: str = "ocr",
):
    """Add an alias if it doesn't already exist."""
    existing = db.query(models.ProductAlias).filter_by(
        product_id=product_id, alias=alias
    ).first()
    if not existing:
        db.add(models.ProductAlias(
            product_id=product_id,
            alias=alias,
            supermarket=supermarket,
            source=source,
        ))


def get_purchases(db: Session, skip: int = 0, limit: int = 50) -> list:
    """Return purchases ordered by date descending, with item count."""
    purchases = (
        db.query(models.Purchase)
        .order_by(desc(models.Purchase.purchase_date))
        .offset(skip)
        .limit(limit)
        .all()
    )
    result = []
    for p in purchases:
        result.append({
            "id": p.id,
            "supermarket": p.store.supermarket if p.store else None,
            "purchase_date": p.purchase_date,
            "total_amount": float(p.total_amount) if p.total_amount else None,
            "item_count": len(p.items),
            "created_at": p.created_at,
        })
    return result


def get_purchase(db: Session, purchase_id: int) -> Optional[dict]:
    """Return a single purchase with all items."""
    p = db.query(models.Purchase).filter_by(id=purchase_id).first()
    if not p:
        return None
    return {
        "id": p.id,
        "supermarket": p.store.supermarket if p.store else None,
        "purchase_date": p.purchase_date,
        "total_amount": float(p.total_amount) if p.total_amount else None,
        "item_count": len(p.items),
        "created_at": p.created_at,
        "items": [
            {
                "id": item.id,
                "raw_name": item.raw_name,
                "canonical_name": item.product.canonical_name if item.product else None,
                "quantity": float(item.quantity),
                "unit_price": float(item.unit_price),
                "total_price": float(item.total_price),
            }
            for item in p.items
        ],
    }


def delete_purchase(db: Session, purchase_id: int) -> bool:
    p = db.query(models.Purchase).filter_by(id=purchase_id).first()
    if not p:
        return False
    db.delete(p)
    db.commit()
    return True


# ─── Products ─────────────────────────────────────────────────────────────────

def get_products(db: Session, search: str = "", skip: int = 0, limit: int = 100) -> list:
    q = db.query(models.Product)
    if search:
        q = q.filter(models.Product.canonical_name.ilike(f"%{search}%"))
    return q.order_by(models.Product.canonical_name).offset(skip).limit(limit).all()


def get_product(db: Session, product_id: int) -> Optional[models.Product]:
    return db.query(models.Product).filter_by(id=product_id).first()


# ─── Price history ────────────────────────────────────────────────────────────

def get_price_history(
    db: Session,
    product_id: int,
    supermarket: str = "",
    days: int = 180,
) -> list:
    since = datetime.utcnow() - timedelta(days=days)
    q = db.query(models.PriceHistory).filter(
        models.PriceHistory.product_id == product_id,
        models.PriceHistory.scraped_at >= since,
    )
    if supermarket:
        q = q.filter(models.PriceHistory.supermarket == supermarket)
    return q.order_by(models.PriceHistory.scraped_at).all()


# ─── Analytics ────────────────────────────────────────────────────────────────

def get_cheapest_supermarket(db: Session, days: int = 30) -> list:
    """Average price per supermarket over the last N days."""
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(
            models.PriceHistory.supermarket,
            func.avg(models.PriceHistory.price).label("avg_price"),
            func.count(models.PriceHistory.id).label("data_points"),
        )
        .filter(models.PriceHistory.scraped_at >= since)
        .group_by(models.PriceHistory.supermarket)
        .order_by(func.avg(models.PriceHistory.price))
        .all()
    )
    return [
        {
            "supermarket": r.supermarket,
            "avg_price": round(float(r.avg_price), 4),
            "data_points": r.data_points,
        }
        for r in rows
    ]


def get_monthly_spending(db: Session) -> list:
    """Total spending grouped by month."""
    rows = (
        db.query(
            func.to_char(models.Purchase.purchase_date, "YYYY-MM").label("month"),
            func.sum(models.Purchase.total_amount).label("total"),
            func.count(models.Purchase.id).label("purchase_count"),
        )
        .filter(models.Purchase.total_amount.isnot(None))
        .group_by(text("month"))
        .order_by(text("month"))
        .all()
    )
    return [
        {
            "month": r.month,
            "total": round(float(r.total), 2),
            "purchase_count": r.purchase_count,
        }
        for r in rows
    ]
