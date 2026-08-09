"""
Scraper template for mytek.tn

Unlike Tunisianet, I haven't been able to fetch Mytek's HTML at all from
this sandbox, so I genuinely don't know its markup or its search URL
pattern. This file is a *template* following the same shape as the
Tunisianet scraper -- you'll need to fill in the two TODOs below.

How to fill them in (5 minutes):
1. Go to mytek.tn in your browser, use the search bar for something
   like "power bank", and copy the resulting URL -> paste it as
   SEARCH_URL_TEMPLATE below (replace the search term with {query}).
2. Right-click a product card in the results -> Inspect. Note the CSS
   class around each product (often something like "product-item" or
   "product-miniature" if it's also PrestaShop-based, which many
   Tunisian e-commerce sites are). Fill in SELECTORS.

Once both scrapers use the same ProductListing shape, the aggregator
in aggregate.py doesn't care which site it came from.
"""

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# TODO: replace with Mytek's real search URL, found by searching on the
# site in your browser and copying the resulting address bar URL.
SEARCH_URL_TEMPLATE = "https://www.mytek.tn/recherche?controller=search&s={query}"

# TODO: replace with real selectors found via right-click -> Inspect.
SELECTORS = {
    "product_card": "article.product-miniature, div.product-miniature",
    "name": "h3.product-title a, a.product-title",
    "price": "span.price, span.product-price",
}


@dataclass
class ProductListing:
    source: str
    name: str
    price_tnd: float
    url: str


def _parse_price(raw: str) -> float:
    cleaned = raw.replace("DT", "").replace("dt", "").strip()
    cleaned = cleaned.replace(" ", "").replace("\xa0", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        digits = "".join(c for c in cleaned if c.isdigit() or c == ".")
        return float(digits) if digits else 0.0


def search_mytek(query: str, max_results: int = 10) -> List[ProductListing]:
    url = SEARCH_URL_TEMPLATE.format(query=query.replace(" ", "+"))
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    cards = soup.select(SELECTORS["product_card"])
    for card in cards[:max_results]:
        name_el = card.select_one(SELECTORS["name"])
        price_el = card.select_one(SELECTORS["price"])
        if not name_el or not price_el:
            continue
        name = name_el.get_text(strip=True)
        price = _parse_price(price_el.get_text(strip=True))
        link = name_el.get("href", "")
        results.append(ProductListing(
            source="Mytek",
            name=name,
            price_tnd=price,
            url=link,
        ))
    return results


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "power bank"
    found = search_mytek(q)
    if not found:
        print(f"0 results for '{q}'. Fill in the TODOs at the top of this "
              f"file with Mytek's real search URL and selectors.")
    for p in found:
        print(f"{p.price_tnd:>8.3f} DT  {p.name}  ({p.url})")
