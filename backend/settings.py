import os

from sqlalchemy import URL

SUPERMARKETS = ("mercadona", "carrefour", "bonpreu", "elcorteingles", "alcampo")
DATABASE_URL = os.getenv("DATABASE_URL") or URL.create(
    "postgresql+psycopg2",
    username=os.getenv("POSTGRES_USER", "stalvia"),
    password=os.getenv("POSTGRES_PASSWORD", "stalvia"),
    host=os.getenv("POSTGRES_HOST", "postgres"),
    port=5432,
    database=os.getenv("POSTGRES_DB", "stalvia"),
)
MAX_IMAGE_BYTES = 8 * 1024 * 1024
