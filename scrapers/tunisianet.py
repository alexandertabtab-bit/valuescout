"""
Scraper for tunisianet.com.tn

CONFIRMED WORKING -- both the search endpoint and selectors below were
verified against live HTML, not guessed:

  - search URL:    tunisianet.com.tn/recherche?s=YOUR+TERM
                    (confirmed working for arbitrary terms, e.g.
                    "power bank", "casque bluetooth" -- not limited to
                    pre-mapped categories)
  - product card:  article.product-miniature
  - name:          h2.product-title a
  - description:   div.descrip a   (contains specs -- mAh, W, ports,
                    protections -- used by features.py)
  - price:         span.price   (format: "29,000 DT")
"""

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List
from urllib.parse import quote_plus

HEADERS = {
    # A normal browser user-agent avoids being blocked as an obvious bot.
    # Be a polite scraper: don't hammer the site, add delays if you scale up.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

SEARCH_URL = "https://www.tunisianet.com.tn/recherche"

SELECTORS = {
    "product_card": "article.product-miniature",
    "name": "h2.product-title a",
    "description": "div.descrip a",
    "price": "span.price",
}


@dataclass
class ProductListing:
    source: str
    name: str
    description: str
    price_tnd: float
    url: str


def _parse_price(raw: str) -> float:
    """Turn '29,000 DT' into 29.0 (Tunisian dinar, 3-decimal millime format)."""
    cleaned = raw.replace("DT", "").replace("Prix", "").strip()
    cleaned = cleaned.replace(" ", "").replace("\xa0", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        digits = "".join(c for c in cleaned if c.isdigit() or c == ".")
        return float(digits) if digits else 0.0


def search_tunisianet(query: str, max_results: int = 24) -> List[ProductListing]:
    """
    Searches Tunisianet for any term via its real search page (24 results
    per page -- pagination isn't implemented here, but could be added by
    requesting &page=2, &page=3, etc. if you want more than 24 results).
    """
    params = {"s": query}
    resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    cards = soup.select(SELECTORS["product_card"])
    for card in cards[:max_results]:
        name_el = card.select_one(SELECTORS["name"])
        price_el = card.select_one(SELECTORS["price"])
        desc_el = card.select_one(SELECTORS["description"])
        if not name_el or not price_el:
            continue
        results.append(ProductListing(
            source="Tunisianet",
            name=name_el.get_text(strip=True),
            description=desc_el.get_text(strip=True) if desc_el else "",
            price_tnd=_parse_price(price_el.get_text(strip=True)),
            url=name_el.get("href", ""),
        ))
    return results


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "power bank"
    found = search_tunisianet(q)
    for p in found:
        print(f"{p.price_tnd:>8.3f} DT  {p.name}")
        if p.description:
            print(f"           {p.description}")
