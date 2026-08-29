# StalvIA 🛒

> **Estalvia** (català: _estalviar_, to save) + **IA** (Intel·ligència Artificial)

Aplicació web personal per comparar preus de productes de supermercat a Catalunya a partir d'una fotografia del tiquet de compra.

![StalvIA](https://img.shields.io/badge/StalvIA-v0.1.0-green?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql)

---

## Què fa StalvIA?

1. **Fotografies el tiquet** de qualsevol dels tres supermercat suportats
2. **Claude Vision (IA)** extreu tots els productes, quantitats i preus via OCR
3. **Scrapers en temps real** busquen el preu actual de cada producte als tres supers
4. **Comparativa** producte a producte amb el preu mínim destacat i l'estalvi total potencial
5. **Historial de preus** emmagatzemat per analitzar l'evolució temporal i fer estudis de mercat

### Supermercat suportats
| Supermercat | Mètode | Estat |
|---|---|---|
| **Mercadona** | API no oficial (community) | ✅ |
| **Bonpreu / Esclat** | Web scraping (Playwright) | 🚧 |
| **Carrefour** | Web scraping (Playwright) | 🚧 |

---

## Arquitectura

```
Internet
    │
    ▼
Cloudflare Access (autenticació)
    │
    ▼
Cloudflare Tunnel (HTTPS automàtic)
    │
    ▼
LXC Proxmox (10.8.1.19)
    ├── nginx (reverse proxy :8080)
    ├── frontend  (React + Vite)
    ├── backend   (FastAPI + Python 3.12)
    ├── postgres  (PostgreSQL 16)
    └── redis     (cache scraping ~4h TTL)
         │
         ▼
    Cloudflare R2 (imatges tiquets)
```

### Stack tecnològic

| Capa | Tecnologia |
|---|---|
| Frontend | React 18 + Vite + TailwindCSS |
| Backend | Python 3.12 + FastAPI |
| Base de dades | PostgreSQL 16 + SQLAlchemy + Alembic |
| Cache | Redis 7 (TTL 4h per scraping) |
| OCR / Vision | Claude Vision API (Anthropic) |
| Scraping | Playwright (headless Chromium) + httpx |
| Infraestructura | Proxmox LXC + Docker Compose |
| Exposició | Cloudflare Tunnel + Cloudflare Access |
| Emmagatzematge | Cloudflare R2 (imatges tiquets) |

---

## Model de dades

Dissenyat per a anàlisi temporal de preus des del primer dia:

```
categories (jeràrquic, parent_id)
brands (nom, is_private_label)

stores
  └── purchases
        └── purchase_items ──→ products
                                  ├── product_aliases  (normalització OCR, pg_trgm)
                                  ├── price_history    (sèrie temporal de preus)
                                  ├── promotions       (2x1, descomptes, etc.)
                                  ├── price_alerts     (notificació quan baixa el preu)
                                  └── shopping_list_items

shopping_lists
  └── shopping_list_items
```

### Taules principals

| Taula | Propòsit |
|---|---|
| `products` | Catàleg canònic de productes |
| `product_aliases` | Variants de nom per OCR i scrapers (`pg_trgm`) |
| `price_history` | Sèrie temporal de preus per producte i supermercat |
| `purchases` | Tiquets escanejats (data, botiga, total) |
| `purchase_items` | Línia a línia del tiquet (nom raw + producte normalitzat) |
| `stores` | Botigues físiques amb coordenades |
| `promotions` | Ofertes amb data d'inici i fi |
| `price_alerts` | Alertes quan un producte arriba a preu objectiu |
| `shopping_lists` | Llistes de la compra planificades |

### Consultes analítiques que habilita

```sql
-- Evolució del preu de la llet a Mercadona (últims 6 mesos)
SELECT DATE_TRUNC('week', scraped_at), AVG(price)
FROM price_history
WHERE product_id = 42 AND supermarket = 'mercadona'
GROUP BY 1 ORDER BY 1;

-- Quin super ha estat més barat de mitjana aquest mes?
SELECT supermarket, AVG(price) as avg_price
FROM price_history
WHERE scraped_at > NOW() - INTERVAL '30 days'
GROUP BY supermarket ORDER BY avg_price;

-- Quant m'hauria estalviat comprant al super més barat?
SELECT p.purchase_date, p.total_amount as pagat,
       SUM(ph_min.min_price * pi.quantity) as preu_optim
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

## Estructura del projecte

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
│   ├── database.py          # Connexió PostgreSQL
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── mercadona.py     # API no oficial
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
│       │   ├── TicketUploader.jsx
│       │   ├── ComparisonTable.jsx
│       │   ├── ProductRow.jsx
│       │   └── PriceSummary.jsx
│       ├── pages/
│       │   ├── Home.jsx
│       │   ├── History.jsx
│       │   └── Analytics.jsx
│       ├── hooks/
│       │   └── useTicketAnalysis.js
│       └── services/
│           └── api.js
│
└── nginx/
    └── nginx.conf
```

---

## Instal·lació i desplegament

### Prerequisits

- Proxmox amb LXC Debian 12
- Docker + Docker Compose plugin
- Compte Cloudflare amb domini configurat
- Clau API d'Anthropic

### 1. Crear el LXC a Proxmox

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

### 2. Instal·lar Docker

```bash
pct enter 120
apt update && apt install -y curl git
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin
```

### 3. Clonar el repositori

```bash
cd /opt
git clone https://github.com/el-teu-usuari/stalvia.git
cd stalvia
cp .env.example .env
# Editar .env amb les teves credencials
```

### 4. Configurar variables d'entorn

```bash
nano .env
```

```env
ANTHROPIC_API_KEY=sk-ant-...
POSTGRES_DB=stalvia
POSTGRES_USER=stalvia
POSTGRES_PASSWORD=password_segur
DATABASE_URL=postgresql://stalvia:password_segur@postgres:5432/stalvia
REDIS_URL=redis://redis:6379
```

### 5. Arrancar els serveis

```bash
docker compose up -d
docker compose exec backend alembic upgrade head
```

### 6. Cloudflare Tunnel

Al dashboard de Cloudflare Zero Trust → Networks → Tunnels → el teu túnel → **Add public hostname**:

```
Subdomain : stalvia
Domain    : el-teu-domini.com
Service   : http://10.8.1.19:8080
```

---

## Ús

1. Obre `https://stalvia.el-teu-domini.com`
2. Fes clic a **"Analitza tiquet"** i puja la foto
3. StalvIA extreu els productes via Claude Vision
4. Es mostren els preus actuals als 3 supers
5. El producte més barat es destaca en verd ✓
6. Veus el total de compra a cada supermercat i l'estalvi potencial

---

## Roadmap

- [x] Arquitectura i model de dades
- [x] Infraestructura Docker + Proxmox
- [ ] Backend FastAPI + endpoints
- [ ] Scrapers Mercadona (API)
- [ ] Scrapers Carrefour + Bonpreu (Playwright)
- [ ] Integració Claude Vision API
- [ ] Frontend React — comparativa de preus
- [ ] Pàgina d'historial de compres
- [ ] Gràfics d'evolució de preus (Analytics)
- [ ] Alertes de preu
- [ ] Llistes de la compra
- [ ] Integració Cloudflare R2 per a imatges

---

## Llicència

Ús personal. No destinat a distribució pública.
