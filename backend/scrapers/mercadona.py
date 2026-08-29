"""
Scraper Mercadona via API no oficial de la comunitat.
Documentació: https://tienda.mercadona.es/api/
"""
import httpx

BASE_URL = "https://tienda.mercadona.es/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept": "application/json",
}


async def search(query: str) -> dict | None:
    """Cerca un producte a Mercadona i retorna el primer resultat."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{BASE_URL}/search/",
                params={"query": query, "lang": "es", "wh": "vlc1"},
                headers=HEADERS,
            )
            r.raise_for_status()
            data = r.json()

        results = data.get("results", {}).get("items", [])
        if not results:
            return None

        item = results[0]
        price_info = item.get("price_instructions", {})

        return {
            "name": item.get("display_name"),
            "price": float(price_info.get("unit_price", 0)),
            "unit_size": price_info.get("unit_size"),
            "unit_name": price_info.get("unit_name"),
            "price_per_unit": float(price_info.get("reference_price", 0)),
            "image": item.get("thumbnail"),
            "url": f"https://tienda.mercadona.es/product/{item['id']}",
            "in_promotion": price_info.get("is_new", False),
        }

    except Exception as e:
        print(f"[Mercadona] Error cercant '{query}': {e}")
        return None
