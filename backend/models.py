from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    parent = relationship("Category", remote_side=[id], backref="children")
    products = relationship("Product", back_populates="category")


class Brand(Base):
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    is_private_label = Column(Boolean, default=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    products = relationship("Product", back_populates="brand")


class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True)
    supermarket = Column(String(50), nullable=False)  # mercadona, carrefour, bonpreu
    name = Column(String(150), nullable=False)
    address = Column(String(250))
    city = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)
    store_code = Column(String(50))
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    purchases = relationship("Purchase", back_populates="store")
    price_history = relationship("PriceHistory", back_populates="store")
    promotions = relationship("Promotion", back_populates="store")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    canonical_name = Column(String(250), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    barcode = Column(String(50), nullable=True, unique=True)
    unit_size = Column(Float)
    unit_type = Column(String(20))  # kg, l, ud, etc.
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    category = relationship("Category", back_populates="products")
    brand = relationship("Brand", back_populates="products")
    aliases = relationship("ProductAlias", back_populates="product")
    price_history = relationship("PriceHistory", back_populates="product")
    promotions = relationship("Promotion", back_populates="product")
    purchase_items = relationship("PurchaseItem", back_populates="product")
    alert = relationship("PriceAlert", back_populates="product")


class ProductAlias(Base):
    __tablename__ = "product_aliases"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    alias = Column(String(250), nullable=False)
    supermarket = Column(String(50), nullable=True)  # null = genèric
    source = Column(String(20), default="ocr")  # ocr, manual, scraper
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    product = relationship("Product", back_populates="aliases")


class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    purchase_date = Column(DateTime, nullable=False)
    receipt_hash = Column(String(64), unique=True, nullable=True)
    ticket_image_url = Column(String(500))  # URL a Cloudflare R2
    total_amount = Column(Numeric(10, 2))
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    store = relationship("Store", back_populates="purchases")
    items = relationship(
        "PurchaseItem", back_populates="purchase", cascade="all, delete-orphan"
    )


class PurchaseItem(Base):
    __tablename__ = "purchase_items"
    id = Column(Integer, primary_key=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    raw_name = Column(String(250), nullable=False)  # nom exacte del tiquet
    quantity = Column(Float, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)

    purchase = relationship("Purchase", back_populates="items")
    product = relationship("Product", back_populates="purchase_items")


class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    supermarket = Column(String(50), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    source = Column(String(20), nullable=False, default="manual")
    source_url = Column(String(1000))
    scraped_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    in_promotion = Column(Boolean, default=False)

    product = relationship("Product", back_populates="price_history")
    store = relationship("Store", back_populates="price_history")


class Promotion(Base):
    __tablename__ = "promotions"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    supermarket = Column(String(50), nullable=False)
    type = Column(String(30))  # 2x1, descuento_pct, precio_fijo
    discount_value = Column(Numeric(10, 2))
    price_with_promo = Column(Numeric(10, 2))
    valid_from = Column(DateTime)
    valid_until = Column(DateTime)
    scraped_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    product = relationship("Product", back_populates="promotions")
    store = relationship("Store", back_populates="promotions")


class PriceAlert(Base):
    __tablename__ = "price_alerts"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    supermarket = Column(String(50), nullable=True)  # null = qualsevol
    target_price = Column(Numeric(10, 2), nullable=False)
    triggered_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    product = relationship("Product", back_populates="alert")


class ShoppingList(Base):
    __tablename__ = "shopping_lists"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    completed_at = Column(DateTime, nullable=True)

    items = relationship("ShoppingListItem", back_populates="shopping_list")


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"
    id = Column(Integer, primary_key=True)
    list_id = Column(Integer, ForeignKey("shopping_lists.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    quantity = Column(Float, default=1)
    purchased = Column(Boolean, default=False)

    shopping_list = relationship("ShoppingList", back_populates="items")


# Keep migration autogeneration aligned with the versioned PostgreSQL indexes.

Index(
    "idx_products_canonical_trgm",
    Product.canonical_name,
    postgresql_using="gin",
    postgresql_ops={"canonical_name": "gin_trgm_ops"},
)
Index(
    "idx_product_aliases_trgm",
    ProductAlias.alias,
    postgresql_using="gin",
    postgresql_ops={"alias": "gin_trgm_ops"},
)
Index(
    "idx_price_history_product_store_date",
    PriceHistory.product_id,
    PriceHistory.supermarket,
    PriceHistory.scraped_at,
)
