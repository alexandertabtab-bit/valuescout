"""
Scraper for tunisianet.com.tn

CONFIRMED WORKING as of this session -- selectors below were verified
against live HTML, not guessed:
  - product card:  article.product-miniature
  - name:          h2.product-title a
  - description:   div.descrip a   (this text contains the specs --
                    mAh, W, ports, protections -- useful later for the
                    checkbox-matching feature)
  - price:         span.price   (format: "29,000 DT")

Also confirmed: the free-text search endpoint
(/recherche?controller=search&s=...) returned 0 results for a query
that likely just had no matches -- it's not necessarily broken. But
category pages are the reliable, verified path, and they come with
free bonus data: real brand and capacity (mAh) filters baked into the
page, which map nicely onto the "6 checkboxes" feature idea.

This scraper browses a known category page rather than free-text
searching, since that's what's actually been verified end-to-end.
CATEGORY_URLS below currently only has power bank mapped -- add more
categories as you need them (visit the site, browse to the category,
copy its URL).
"""

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Optional

HEADERS = {
    # A normal browser user-agent avoids being blocked as an obvious bot.
    # Be a polite scraper: don't hammer the site, add delays if you scale up.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Map a friendly category name to its real Tunisianet category URL.
# Add more by browsing the category on the site and copying the URL.
CATEGORY_URLS = {
    "power bank": "https://www.tunisianet.com.tn/636-power-bank-tunisie",
}

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


def _scrape_page(url: str, max_results: int) -> List[ProductListing]:
    resp = requests.get(url, headers=HEADERS, timeout=15)
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


def search_tunisianet(query: str, max_results: int = 24) -> List[ProductListing]:
    """
    Looks up `query` in CATEGORY_URLS and scrapes that category page.
    If the query isn't a known category yet, returns an empty list --
    add the category's real URL to CATEGORY_URLS to support it.
    """
    category_url = CATEGORY_URLS.get(query.lower().strip())
    if not category_url:
        print(f"[info] '{query}' isn't in CATEGORY_URLS yet. "
              f"Browse to it on tunisianet.com.tn and add its URL.")
        return []
    return _scrape_page(category_url, max_results)


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "power bank"
    found = search_tunisianet(q)
    for p in found:
        print(f"{p.price_tnd:>8.3f} DT  {p.name}")
        if p.description:
            print(f"           {p.description}")
