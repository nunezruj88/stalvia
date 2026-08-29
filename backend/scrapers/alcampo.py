"""
Scraper Alcampo (Auchan Group) via Playwright (headless Chromium).
"""
from playwright.async_api import async_playwright
import re


async def search(query: str) -> dict | None:
    """Search for a product at Alcampo and return the first result."""
    url = f"https://www.alcampo.es/compra-online/search/?q={query.replace(' ', '+')}"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            )
            page = await context.new_page()

            await page.goto(url, wait_until="domcontentloaded", timeout=15000)

            # Accept cookies if dialog appears
            try:
                await page.click("#onetrust-accept-btn-handler", timeout=3000)
            except Exception:
                pass

            await page.wait_for_selector(".product-item", timeout=8000)

            card = await page.query_selector(".product-item")
            if not card:
                await browser.close()
                return None

            name_el = await card.query_selector(".product-item__title")
            price_el = await card.query_selector(".product-item__price .value")
            img_el = await card.query_selector("img")
            link_el = await card.query_selector("a")

            name = await name_el.inner_text() if name_el else query
            price_text = await price_el.inner_text() if price_el else "0"
            image = await img_el.get_attribute("src") if img_el else None
            href = await link_el.get_attribute("href") if link_el else ""

            price_clean = re.sub(r"[^\d,.]", "", price_text).replace(",", ".")
            price = float(price_clean) if price_clean else None

            await browser.close()

            return {
                "name": name.strip(),
                "price": price,
                "image": image,
                "url": f"https://www.alcampo.es{href}" if href.startswith("/") else href,
                "in_promotion": False,
            }

    except Exception as e:
        print(f"[Alcampo] Error searching '{query}': {e}")
        return None
