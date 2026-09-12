"""
Scraper El Corte Inglés Supermercado via Playwright (headless Chromium).
"""

import re
from urllib.parse import quote_plus

from .browser import page_context


async def search(query: str) -> dict | None:
    """Search for a product at El Corte Inglés and return the first result."""
    url = f"https://www.elcorteingles.es/supermercado/buscar/?term={quote_plus(query)}"

    try:
        async with page_context() as page:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)

            # Accept cookies if dialog appears
            try:
                await page.click("#onetrust-accept-btn-handler", timeout=3000)
            except Exception:
                pass

            await page.wait_for_selector(".product-card", timeout=8000)

            card = await page.query_selector(".product-card")
            if not card:
                return None

            name_el = await card.query_selector(".product-card__name")
            price_el = await card.query_selector(".product-card__price-current")
            img_el = await card.query_selector("img")
            link_el = await card.query_selector("a")

            name = await name_el.inner_text() if name_el else query
            price_text = await price_el.inner_text() if price_el else ""
            image = await img_el.get_attribute("src") if img_el else None
            href = await link_el.get_attribute("href") if link_el else ""

            price_clean = re.sub(r"[^\d,.]", "", price_text).replace(",", ".")
            price = float(price_clean) if price_clean else None

            return {
                "name": name.strip(),
                "price": price,
                "image": image,
                "url": f"https://www.elcorteingles.es{href}"
                if href.startswith("/")
                else href,
                "in_promotion": False,
            }

    except Exception as e:
        print(f"[ElCorteIngles] Error searching '{query}': {e}")
        raise
