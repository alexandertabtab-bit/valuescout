"""
Combines results from every scraper into one list, and computes the
"sweet spot" value score (the core idea from your original request).

This is the layer that's actually novel about your app -- the
scrapers just fetch prices, this is what turns raw prices into a
recommendation.
"""

from dataclasses import dataclass
from typing import List, Optional
from statistics import median, mean

from scrapers.tunisianet import search_tunisianet, ProductListing
from scrapers.mytek import search_mytek
from features import extract_features, CHECKLIST


@dataclass
class ScoredProduct:
    source: str
    name: str
    price_tnd: float
    url: str
    value_score: float          # 0 to 1, higher = better value
    matched_features: List[str] # which checked boxes this listing satisfies
    total_checked: int          # how many boxes the user checked


def gather_listings(query: str) -> List[ProductListing]:
    """Query every configured source and combine results.

    Each scraper is wrapped in try/except: if one site is down or its
    selectors are stale, you still get results from the others instead
    of the whole search failing.
    """
    listings: List[ProductListing] = []

    try:
        listings.extend(search_tunisianet(query))
    except Exception as e:
        print(f"[warn] Tunisianet search failed: {e}")

    try:
        listings.extend(search_mytek(query))
    except Exception as e:
        print(f"[warn] Mytek search failed: {e}")

    # drop listings where price parsing failed (price == 0)
    return [l for l in listings if l.price_tnd > 0]


def score_listings(
    listings: List[ProductListing],
    selected_features: Optional[List[str]] = None,
) -> List[ScoredProduct]:
    """
    Combines two signals into one value score:

    1. Price positioning -- how close a listing's price is to the
       market median. Cheapest is often cheap for a reason, priciest
       is often paying for brand name; the median is a reasonable
       proxy for "a fair price" per your original idea.

    2. Feature match -- if the user checked boxes (e.g. "fast
       charging", "USB-C"), each listing's description is scanned
       for those features via features.extract_features(), and the
       listing gets credit for each checked box it actually satisfies.

    If selected_features is empty/None, the score is price-only (same
    behavior as before). Weights are 50/50 when features are selected --
    tune WEIGHT_PRICE / WEIGHT_FEATURES below if you want price or
    features to matter more.
    """
    WEIGHT_PRICE = 0.5
    WEIGHT_FEATURES = 0.5

    if not listings:
        return []

    selected_features = selected_features or []
    prices = [l.price_tnd for l in listings]
    med = median(prices)
    price_range = max(prices) - min(prices) or 1
    min_price = min(prices)

    scored = []
    for l in listings:
        matched = []
        if selected_features:
            # Once the user has checked real feature boxes, those boxes
            # already do the job of weeding out low-quality cheap items --
            # so among products that match, lower price should win
            # outright, not be pulled toward the median.
            price_score = 1 - ((l.price_tnd - min_price) / price_range)

            feats = extract_features(f"{l.name} {l.description}")
            for key in selected_features:
                check = CHECKLIST[key]["check"]
                if check(feats):
                    matched.append(key)
            feature_score = len(matched) / len(selected_features)
            value_score = WEIGHT_PRICE * price_score + WEIGHT_FEATURES * feature_score
        else:
            # No features selected: fall back to median-proximity, since
            # without any quality signal, "priced like everything else"
            # is the only proxy we have for "probably not junk / not markup".
            distance_from_median = abs(l.price_tnd - med) / price_range
            value_score = 1 - distance_from_median

        scored.append(ScoredProduct(
            source=l.source,
            name=l.name,
            price_tnd=l.price_tnd,
            url=l.url,
            value_score=round(value_score, 3),
            matched_features=matched,
            total_checked=len(selected_features),
        ))

    return sorted(scored, key=lambda p: p.value_score, reverse=True)


def run(query: str, selected_features: Optional[List[str]] = None):
    listings = gather_listings(query)
    if not listings:
        print(f"No listings found for '{query}'. Check that the scrapers "
              f"are calibrated to each site's real HTML (see the TODOs in "
              f"scrapers/tunisianet.py and scrapers/mytek.py).")
        return

    scored = score_listings(listings, selected_features)
    prices = [l.price_tnd for l in listings]

    print(f"\nResults for '{query}': {len(listings)} listings found")
    print(f"Price range: {min(prices):.3f} - {max(prices):.3f} DT | "
          f"Median: {median(prices):.3f} DT | Mean: {mean(prices):.3f} DT")
    if selected_features:
        labels = [CHECKLIST[k]["label"] for k in selected_features]
        print(f"Checked features: {', '.join(labels)}\n")
    else:
        print()

    for p in scored:
        marker = " <- sweet spot" if p == scored[0] else ""
        feat_note = ""
        if p.total_checked:
            feat_note = f"  [{len(p.matched_features)}/{p.total_checked} features matched]"
        print(f"[{p.value_score:.2f}] {p.price_tnd:>8.3f} DT  "
              f"({p.source}) {p.name}{feat_note}{marker}")


if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "power bank"
    # Example: check "fast charging" and "USB-C" as the user's picks
    run(query, selected_features=["fast_charging", "usb_c"])

# --- Status ---
# DONE: Tunisianet scraper -- confirmed working against real HTML
#       (article.product-miniature / h2.product-title a / span.price).
# DONE: Checklist-based feature scoring (features.py) -- matches user
#       checkboxes against real spec text pulled from descriptions.
#
# --- Next upgrades, roughly in order of impact ---
# 1. Calibrate scrapers/mytek.py the same way we did Tunisianet: fetch
#    a real category page, find article/product container class via
#    the same "try candidate selectors" trick, confirm price/name tags.
# 2. Add more categories to CATEGORY_URLS in scrapers/tunisianet.py --
#    right now only "power bank" is mapped. Browse the site, copy URLs.
# 3. Add caching (e.g. a SQLite table keyed by query+timestamp) so you
#    don't re-scrape on every search -- also makes you a better citizen
#    of these sites' servers.
# 4. Add a barcode -> product name step (e.g. via UPCitemdb's free tier)
#    so the app can take a barcode as input, not just a category name.
# 5. Once both scrapers work, wrap this in a Streamlit UI: a search
#    box/category dropdown + checkboxes from CHECKLIST + a results
#    table showing score, price, and matched features.
