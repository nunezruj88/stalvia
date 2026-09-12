import asyncio
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright

_lock = asyncio.Lock()
_playwright = None
_browser = None


@asynccontextmanager
async def page_context():
    global _playwright, _browser
    async with _lock:
        if _browser is None or not _browser.is_connected():
            if _playwright is not None:
                await _playwright.stop()
            _playwright = await async_playwright().start()
            _browser = await _playwright.chromium.launch(headless=True)
        context = await _browser.new_context()
    try:
        yield await context.new_page()
    finally:
        await context.close()


async def close_browser():
    global _playwright, _browser
    if _browser is not None:
        await _browser.close()
    if _playwright is not None:
        await _playwright.stop()
    _browser = _playwright = None
