"""Initial schema, frozen at revision 0001."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "brands",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_private_label", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["categories.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "shopping_lists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supermarket", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("address", sa.String(length=250), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("store_code", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("canonical_name", sa.String(length=250), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("brand_id", sa.Integer(), nullable=True),
        sa.Column("barcode", sa.String(length=50), nullable=True),
        sa.Column("unit_size", sa.Float(), nullable=True),
        sa.Column("unit_type", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["brand_id"],
            ["brands.id"],
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("barcode"),
    )
    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("purchase_date", sa.DateTime(), nullable=False),
        sa.Column("receipt_hash", sa.String(length=64), nullable=True),
        sa.Column("ticket_image_url", sa.String(length=500), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("receipt_hash"),
    )
    op.create_table(
        "price_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("supermarket", sa.String(length=50), nullable=True),
        sa.Column("target_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("triggered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("supermarket", sa.String(length=50), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("scraped_at", sa.DateTime(), nullable=True),
        sa.Column("in_promotion", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "product_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=250), nullable=False),
        sa.Column("supermarket", sa.String(length=50), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "promotions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("supermarket", sa.String(length=50), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=True),
        sa.Column("discount_value", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("price_with_promo", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("valid_from", sa.DateTime(), nullable=True),
        sa.Column("valid_until", sa.DateTime(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "purchase_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("raw_name", sa.String(length=250), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.ForeignKeyConstraint(
            ["purchase_id"],
            ["purchases.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "shopping_list_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("list_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("purchased", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["list_id"],
            ["shopping_lists.id"],
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_products_canonical_trgm",
        "products",
        ["canonical_name"],
        postgresql_using="gin",
        postgresql_ops={"canonical_name": "gin_trgm_ops"},
    )
    op.create_index(
        "idx_product_aliases_trgm",
        "product_aliases",
        ["alias"],
        postgresql_using="gin",
        postgresql_ops={"alias": "gin_trgm_ops"},
    )
    op.create_index(
        "idx_price_history_product_store_date",
        "price_history",
        ["product_id", "supermarket", "scraped_at"],
    )


def downgrade():
    op.drop_table("shopping_list_items")
    op.drop_table("purchase_items")
    op.drop_table("promotions")
    op.drop_table("product_aliases")
    op.drop_table("price_history")
    op.drop_table("price_alerts")
    op.drop_table("purchases")
    op.drop_table("products")
    op.drop_table("stores")
    op.drop_table("shopping_lists")
    op.drop_table("categories")
    op.drop_table("brands")
