-- Enable pg_trgm for fuzzy product name matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Index for fast trigram search on product aliases
CREATE INDEX IF NOT EXISTS idx_product_aliases_trgm
  ON product_aliases USING GIN (alias gin_trgm_ops);

-- Index for fast trigram search on canonical product names
CREATE INDEX IF NOT EXISTS idx_products_canonical_trgm
  ON products USING GIN (canonical_name gin_trgm_ops);
