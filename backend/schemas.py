from datetime import datetime

from pydantic import BaseModel, ConfigDict

# ─── Price data ───────────────────────────────────────────────────────────────


class SupermarketPrice(BaseModel):
    name: str | None = None
    price: float | None = None
    image: str | None = None
    url: str | None = None
    in_promotion: bool = False


class ProductComparison(BaseModel):
    raw_name: str
    canonical_name: str | None = None
    quantity: float = 1
    price_paid: float | None = None
    prices: dict[str, SupermarketPrice | None]
    best_supermarket: str | None = None
    best_price: float | None = None


class TicketSummary(BaseModel):
    total_paid: float
    totals_by_super: dict[str, float]
    cheapest_supermarket: str | None = None
    cheapest_total: float | None = None
    potential_savings: float = 0


class TicketResponse(BaseModel):
    purchase_id: int | None = None
    supermarket: str | None = None
    date: str | None = None
    total_paid: float | None = None
    products: list[ProductComparison]
    summary: TicketSummary


# ─── Purchases ────────────────────────────────────────────────────────────────


class PurchaseItemSummary(BaseModel):
    id: int
    raw_name: str
    canonical_name: str | None = None
    quantity: float
    unit_price: float
    total_price: float

    model_config = ConfigDict(from_attributes=True)


class PurchaseSummary(BaseModel):
    id: int
    supermarket: str | None = None
    purchase_date: datetime
    total_amount: float | None = None
    item_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseDetail(PurchaseSummary):
    items: list[PurchaseItemSummary] = []

    model_config = ConfigDict(from_attributes=True)


# ─── Products ─────────────────────────────────────────────────────────────────


class ProductSummary(BaseModel):
    id: int
    canonical_name: str
    unit_size: float | None = None
    unit_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductAliasSummary(BaseModel):
    id: int
    alias: str
    supermarket: str | None = None
    source: str

    model_config = ConfigDict(from_attributes=True)


class ProductDetail(ProductSummary):
    aliases: list[ProductAliasSummary] = []

    model_config = ConfigDict(from_attributes=True)


# ─── Analytics ────────────────────────────────────────────────────────────────


class PricePoint(BaseModel):
    supermarket: str
    price: float
    scraped_at: datetime
    in_promotion: bool = False

    model_config = ConfigDict(from_attributes=True)


class SupermarketAvg(BaseModel):
    supermarket: str
    avg_price: float
    data_points: int


class SpendingByMonth(BaseModel):
    month: str
    total: float
    purchase_count: int


class ManualProductResponse(BaseModel):
    product_id: int
    canonical_name: str
    price_saved: bool
    message: str
