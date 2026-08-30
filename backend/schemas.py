from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# ─── Price data ───────────────────────────────────────────────────────────────

class SupermarketPrice(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    image: Optional[str] = None
    url: Optional[str] = None
    in_promotion: bool = False


class ProductComparison(BaseModel):
    raw_name: str
    canonical_name: Optional[str] = None
    quantity: float = 1
    price_paid: Optional[float] = None
    prices: dict[str, Optional[SupermarketPrice]]
    best_supermarket: Optional[str] = None
    best_price: Optional[float] = None


class TicketSummary(BaseModel):
    total_paid: float
    totals_by_super: dict[str, float]
    cheapest_supermarket: Optional[str] = None
    cheapest_total: Optional[float] = None
    potential_savings: float = 0


class TicketResponse(BaseModel):
    purchase_id: Optional[int] = None
    supermarket: Optional[str] = None
    date: Optional[str] = None
    total_paid: Optional[float] = None
    products: list[ProductComparison]
    summary: TicketSummary


# ─── Purchases ────────────────────────────────────────────────────────────────

class PurchaseItemSummary(BaseModel):
    id: int
    raw_name: str
    canonical_name: Optional[str] = None
    quantity: float
    unit_price: float
    total_price: float

    class Config:
        from_attributes = True


class PurchaseSummary(BaseModel):
    id: int
    supermarket: Optional[str] = None
    purchase_date: datetime
    total_amount: Optional[float] = None
    item_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class PurchaseDetail(PurchaseSummary):
    items: list[PurchaseItemSummary] = []

    class Config:
        from_attributes = True


# ─── Products ─────────────────────────────────────────────────────────────────

class ProductSummary(BaseModel):
    id: int
    canonical_name: str
    unit_size: Optional[float] = None
    unit_type: Optional[str] = None

    class Config:
        from_attributes = True


class ProductAliasSummary(BaseModel):
    id: int
    alias: str
    supermarket: Optional[str] = None
    source: str

    class Config:
        from_attributes = True


class ProductDetail(ProductSummary):
    aliases: list[ProductAliasSummary] = []

    class Config:
        from_attributes = True


# ─── Analytics ────────────────────────────────────────────────────────────────

class PricePoint(BaseModel):
    supermarket: str
    price: float
    scraped_at: datetime
    in_promotion: bool = False

    class Config:
        from_attributes = True


class SupermarketAvg(BaseModel):
    supermarket: str
    avg_price: float
    data_points: int


class SpendingByMonth(BaseModel):
    month: str
    total: float
    purchase_count: int
