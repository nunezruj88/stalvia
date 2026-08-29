# StalvIA 🛒

> **Estalvia** (Catalan: _estalviar_, to save) + **IA** (Artificial Intelligence)

Personal web app to compare supermarket prices in Catalonia from a photo of a purchase receipt.

![StalvIA](https://img.shields.io/badge/StalvIA-v0.1.0-green?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql)

---

## What does StalvIA do?

1. **Photograph your receipt** from any of the three supported supermarkets
2. **Claude Vision (AI)** extracts all products, quantities and prices via OCR
3. **Real-time scrapers** fetch the current price of each product at all three supermarkets
4. **Product-by-product comparison** with the lowest price highlighted and total potential savings
5. **Price history** stored for temporal analysis and market research

### Supported supermarkets

| Supermarket | Method | Status |
|---|---|---|
| **Mercadona** | Unofficial community API | ✅ |
| **Bonpreu / Esclat** | Web scraping (Playwright) | 🚧 |
| **El Corte Inglés** | Web scraping (Playwright) | 🚧 |
| **Alcampo** | Web scraping (Playwright) | 🚧 |
| **Carrefour** | Web scraping (Playwright) | 🚧 |

---

## Architecture

```
Internet
    │
    ▼
Cloudflare Access (authentication)
    │
    ▼
Cloudflare Tunnel (automatic HTTPS)
    │
    ▼
Proxmox LXC (10.8.1.19)
    ├── nginx (reverse proxy :8080)
    ├── frontend  (React + Vite)
    ├── backend   (FastAPI + Python 3.12)
    ├── postgres  (PostgreSQL 16)
    └── redis     (scraping cache ~4h TTL)
         │
         ▼
    Cloudflare R2 (receipt images)
```

### Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + TailwindCSS |
| Backend | Python 3.12 + FastAPI |
| Database | PostgreSQL 16 + SQLAlchemy + Alembic |
| Cache | Redis 7 (4h TTL for scraping) |
| OCR / Vision | Claude Vision API (Anthropic) |
| Scraping | Playwright (headless Chromium) + httpx |
| Infrastructure | Proxmox LXC + Docker Compose |
| Exposure | Cloudflare Tunnel + Cloudflare Access |
| Storage | Cloudflare R2 (receipt images) |

---

## Data model

Designed for time-series price analysis from day one:

```
categories (hierarchical, parent_id)
brands (name, is_private_label)

stores
  └── purchases
        └── purchase_items ──→ products
                                  ├── product_aliases  (OCR normalisation, pg_trgm)
                                  ├── price_history    (time-series price data)
                                  ├── promotions       (2-for-1, discounts, etc.)
                                  ├── price_alerts     (notify when price drops)
                                  └── shopping_list_items

shopping_lists
  └── shopping_list_items
```

### Main tables

| Table | Purpose |
|---|---|
| `products` | Canonical product catalogue |
| `product_aliases` | Name variants for OCR and scrapers (`pg_trgm` fuzzy match) |
| `price_history` | Time-series prices per product and supermarket |
| `purchases` | Scanned receipts (date, store, total) |
| `purchase_items` | Line-by-line receipt data (raw name + normalised product) |
| `stores` | Physical store locations with coordinates |
| `promotions` | Offers with start and end dates |
| `price_alerts` | Alerts when a product reaches a target price |
| `shopping_lists` | Planned shopping lists |

### Analytical queries this enables

```sql
-- Price evolution of milk at Mercadona over the last 6 months
SELECT DATE_TRUNC('week', scraped_at), AVG(price)
FROM price_history
WHERE product_id = 42 AND supermarket = 'mercadona'
GROUP BY 1 ORDER BY 1;

-- Which supermarket has been cheapest on average this month?
SELECT supermarket, AVG(price) as avg_price
FROM price_history
WHERE scraped_at > NOW() - INTERVAL '30 days'
GROUP BY supermarket ORDER BY avg_price;

-- How much would I have saved buying at the cheapest supermarket?
SELECT p.purchase_date, p.total_amount as paid,
       SUM(ph_min.min_price * pi.quantity) as optimal_total
FROM purchases p
JOIN purchase_items pi ON pi.purchase_id = p.id
JOIN LATERAL (
  SELECT MIN(price) as min_price FROM price_history
  WHERE product_id = pi.product_id
    AND scraped_at::date = p.purchase_date
) ph_min ON true
GROUP BY p.id;
```

---

## Project structure

```
stalvia/
├── docker-compose.yml
├── .env.example
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py              # FastAPI app + endpoints
│   ├── models.py            # SQLAlchemy models
│   ├── database.py          # PostgreSQL connection
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── mercadona.py     # Unofficial API
│   │   ├── carrefour.py     # Playwright scraper
│   │   └── bonpreu.py       # Playwright scraper
│   └── migrations/          # Alembic migrations
│       ├── env.py
│       └── versions/
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── components/
│       │   ├── ComparisonTable.jsx
│       │   ├── ProductRow.jsx
│       │   └── PriceSummary.jsx
│       ├── pages/
│       │   ├── Home.jsx
│       │   ├── History.jsx
│       │   └── Analytics.jsx
│       └── services/
│           └── api.js
│
└── nginx/
    └── nginx.conf
```

---

## Installation & deployment

### Prerequisites

- Proxmox with a Debian 12 LXC
- Docker + Docker Compose plugin
- Cloudflare account with a configured domain
- Anthropic API key

### 1. Create the LXC in Proxmox

```bash
pveam update
pveam download local debian-12-standard_12.7-1_amd64.tar.zst

pct create 120 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname stalvia \
  --cores 2 \
  --memory 2048 \
  --swap 512 \
  --rootfs local-lvm:10 \
  --net0 name=eth0,bridge=vmbr0,ip=10.8.1.19/24,gw=10.8.1.1 \
  --unprivileged 1 \
  --features nesting=1 \
  --start 1
```

### 2. Install Docker

```bash
pct enter 120
apt update && apt install -y curl git
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin
```

### 3. Clone the repository

```bash
cd /opt
git clone https://github.com/your-username/stalvia.git
cd stalvia
cp .env.example .env
# Edit .env with your credentials
```

### 4. Configure environment variables

```bash
nano .env
```

```env
ANTHROPIC_API_KEY=sk-ant-...
POSTGRES_DB=stalvia
POSTGRES_USER=stalvia
POSTGRES_PASSWORD=a_secure_password
DATABASE_URL=postgresql://stalvia:a_secure_password@postgres:5432/stalvia
REDIS_URL=redis://redis:6379
```

### 5. Start the services

```bash
docker compose up -d
docker compose exec backend alembic upgrade head
```

### 6. Cloudflare Tunnel

In the Cloudflare Zero Trust dashboard → Networks → Tunnels → your tunnel → **Add public hostname**:

```
Subdomain : stalvia
Domain    : your-domain.com
Service   : http://10.8.1.19:8080
```

---

## Usage

1. Open `https://stalvia.your-domain.com`
2. Click **"Analyse receipt"** and upload the photo
3. StalvIA extracts the products via Claude Vision
4. Current prices at all 3 supermarkets are displayed
5. The cheapest product is highlighted in green ✓
6. You see the total basket cost at each supermarket and the potential savings

---

## Roadmap

- [x] Architecture and data model
- [x] Docker + Proxmox infrastructure
- [ ] FastAPI backend endpoints
- [ ] Mercadona scraper (API)
- [ ] Carrefour + Bonpreu scrapers (Playwright)
- [ ] Claude Vision API integration
- [ ] React frontend — price comparison view
- [ ] Purchase history page
- [ ] Price evolution charts (Analytics)
- [ ] Price alerts
- [ ] Shopping lists
- [ ] Cloudflare R2 integration for receipt images

---

## License

Personal use only. Not intended for public distribution.
