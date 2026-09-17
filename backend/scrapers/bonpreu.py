"""Bonpreu storefront search and structured product details."""

from .bonpreu_product import HOST, parse_product, product_id
from .browser import page_context

BASE_URL = f"https://{HOST}"


async def read_page(page, url):
    response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
    if response is None or response.status >= 400:
        raise RuntimeError("Bonpreu blocked or unavailable")


async def read_product(url):
    product_id(url)
    async with page_context() as page:
        await read_page(page, url)
        return parse_product(await page.content(), page.url)


async def search(query: str) -> dict | None:
    # A direct product URL can also be used to validate an individual listing.
    if query.startswith("https://"):
        return await read_product(query)
    raise RuntimeError(
        "Bonpreu name search is not validated; a product URL is required"
    )
