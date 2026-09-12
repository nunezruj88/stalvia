from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import desc, func, text
from sqlalchemy.orm import Session

import models

# ─── Purchases ────────────────────────────────────────────────────────────────


def save_purchase(
    db: Session,
    supermarket: str,
    purchase_date: str | None,
    total_amount: float | None,
    products: list[dict],
    receipt_hash: str | None = None,
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
    parsed_date = datetime.now(timezone.utc).replace(tzinfo=None)
    if purchase_date:
        try:
            parsed_date = datetime.strptime(purchase_date, "%Y-%m-%d")
        except ValueError:
            pass

    purchase = models.Purchase(
        store_id=store.id if store else None,
        purchase_date=parsed_date,
        total_amount=total_amount,
        receipt_hash=receipt_hash,
    )
    db.add(purchase)
    db.flush()

    for p in products:
        # Find or create the canonical product
        product = _find_or_create_product(
            db, p.get("canonical_name") or p.get("raw_name"), p.get("barcode") or None
        )

        # Save raw name as OCR alias if new
        if p.get("raw_name") and p["raw_name"] != product.canonical_name:
            _ensure_alias(db, product.id, p["raw_name"], supermarket, source="ocr")

        # Save purchase item
        unit_price = Decimal(str(p.get("price_paid") or 0))
        quantity = Decimal(str(p.get("quantity") or 1))
        item = models.PurchaseItem(
            purchase_id=purchase.id,
            product_id=product.id,
            raw_name=p.get("raw_name", ""),
            quantity=quantity,
            unit_price=unit_price,
            total_price=Decimal(str(p["total_price"])),
        )
        db.add(item)

        # Store the observed receipt price, not an unverified search candidate.
        # Weighted/discounted lines need unit metadata before entering comparison history.
        if (
            unit_price > 0
            and quantity == quantity.to_integral_value()
            and abs(unit_price * quantity - Decimal(str(p["total_price"])))
            <= Decimal("0.02")
        ):
            db.add(
                models.PriceHistory(
                    product_id=product.id,
                    store_id=store.id if store else None,
                    supermarket=supermarket,
                    price=unit_price,
                    source="receipt",
                    scraped_at=parsed_date,
                )
            )

    db.commit()
    db.refresh(purchase)
    return purchase


def _find_or_create_product(
    db: Session, canonical_name: str, barcode: str | None = None
) -> models.Product:
    name = " ".join(canonical_name.split())
    if barcode:
        product = db.query(models.Product).filter_by(barcode=barcode).first()
        if product:
            return product
        # A new barcode represents a distinct SKU even if the name matches.
    else:
        product = (
            db.query(models.Product)
            .filter(
                func.lower(models.Product.canonical_name) == name.lower(),
                models.Product.barcode.is_(None),
            )
            .first()
        )
        if product:
            return product
    product = models.Product(canonical_name=name, barcode=barcode)
    db.add(product)
    db.flush()
    return product


def _ensure_alias(
    db: Session,
    product_id: int,
    alias: str,
    supermarket: str | None,
    source: str = "ocr",
):
    """Add an alias if it doesn't already exist."""
    existing = (
        db.query(models.ProductAlias)
        .filter_by(product_id=product_id, alias=alias)
        .first()
    )
    if not existing:
        db.add(
            models.ProductAlias(
                product_id=product_id,
                alias=alias,
                supermarket=supermarket,
                source=source,
            )
        )


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
        result.append(
            {
                "id": p.id,
                "supermarket": p.store.supermarket if p.store else None,
                "purchase_date": p.purchase_date,
                "total_amount": float(p.total_amount)
                if p.total_amount is not None
                else None,
                "item_count": len(p.items),
                "created_at": p.created_at,
            }
        )
    return result


def get_purchase(db: Session, purchase_id: int) -> dict | None:
    """Return a single purchase with all items."""
    p = db.query(models.Purchase).filter_by(id=purchase_id).first()
    if not p:
        return None
    return {
        "id": p.id,
        "supermarket": p.store.supermarket if p.store else None,
        "purchase_date": p.purchase_date,
        "total_amount": float(p.total_amount) if p.total_amount is not None else None,
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


def get_products(
    db: Session, search: str = "", skip: int = 0, limit: int = 100
) -> list:
    q = db.query(models.Product)
    if search:
        q = q.filter(models.Product.canonical_name.ilike(f"%{search}%"))
    return q.order_by(models.Product.canonical_name).offset(skip).limit(limit).all()


def get_product(db: Session, product_id: int) -> models.Product | None:
    return db.query(models.Product).filter_by(id=product_id).first()


# ─── Price history ────────────────────────────────────────────────────────────


def get_price_history(
    db: Session,
    product_id: int,
    supermarket: str = "",
    days: int = 180,
) -> list:
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    q = db.query(models.PriceHistory).filter(
        models.PriceHistory.product_id == product_id,
        models.PriceHistory.scraped_at >= since,
    )
    if supermarket:
        q = q.filter(models.PriceHistory.supermarket == supermarket)
    return q.order_by(models.PriceHistory.scraped_at).all()


# ─── Analytics ────────────────────────────────────────────────────────────────


def get_cheapest_supermarket(db: Session, days: int = 30) -> list:
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    rows = (
        db.query(models.PriceHistory)
        .join(models.Product)
        .filter(
            models.PriceHistory.scraped_at >= since,
            models.Product.barcode.isnot(None),
        )
        .order_by(models.PriceHistory.scraped_at.desc(), models.PriceHistory.id.desc())
        .all()
    )
    latest = {}
    for row in rows:
        latest.setdefault((row.supermarket, row.product_id), row.price)
    stores = sorted({s for s, _ in latest})
    if len(stores) < 2:
        return []
    common = set.intersection(
        *({p for s, p in latest if s == store} for store in stores)
    )
    if not common:
        return []
    result = [
        {
            "supermarket": s,
            "avg_price": round(
                float(sum(latest[s, p] for p in common) / len(common)), 4
            ),
            "data_points": len(common),
        }
        for s in stores
    ]
    return sorted(result, key=lambda row: row["avg_price"])


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


def save_manual_product(
    db: Session,
    name: str,
    supermarket: str,
    price: float,
    barcode: str | None = None,
    category: str | None = None,
) -> dict:
    """
    Manually register a product and save its price to price_history.
    Creates or reuses the product and category as needed.
    """
    # Find or create category
    category_obj = None
    if category:
        category_obj = db.query(models.Category).filter_by(name=category).first()
        if not category_obj:
            category_obj = models.Category(name=category)
            db.add(category_obj)
            db.flush()

    # Find or create product
    product = _find_or_create_product(db, name, barcode)

    # Update barcode if provided and not already set
    if barcode and not product.barcode:
        product.barcode = barcode

    # Update category if provided
    if category_obj and not product.category_id:
        product.category_id = category_obj.id

    # Find or create store
    store = db.query(models.Store).filter_by(supermarket=supermarket).first()
    if not store:
        store = models.Store(
            supermarket=supermarket,
            name=supermarket.capitalize(),
        )
        db.add(store)
        db.flush()

    # Save to price_history (always insert — append-only)
    db.add(
        models.PriceHistory(
            product_id=product.id,
            store_id=store.id,
            supermarket=supermarket,
            price=price,
            in_promotion=False,
            source="manual",
        )
    )

    # Save alias with source='manual'
    _ensure_alias(db, product.id, name, supermarket, source="manual")

    db.commit()
    db.refresh(product)

    return {
        "product_id": product.id,
        "canonical_name": product.canonical_name,
        "price_saved": True,
        "message": f'Price {price:.2f}€ saved for "{product.canonical_name}" at {supermarket}',
    }
