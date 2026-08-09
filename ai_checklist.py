"""
Generates a product-category checklist on the fly using the Anthropic
API, for any category that isn't already hand-coded in features.py
(power_bank, casque, souris).

SETUP: requires an ANTHROPIC_API_KEY. Get a free-to-create, pay-as-you-go
key at https://console.anthropic.com -- then either:
  - set it as an environment variable, or
  - if deploying on Streamlit Cloud, add it in your app's Settings ->
    Secrets as: ANTHROPIC_API_KEY = "sk-..."

COST CONTROL: results are cached to checklist_cache.json on disk, so the
same search term is only ever sent to the API once. Every other search
for "power bank" (or whatever) after the first reuses the cached result
for free. This is the difference between "costs pennies total" and
"costs money every single search" -- don't remove the caching.

LIMITATION: on some free hosts (like Streamlit Community Cloud), the
disk resets when the app restarts/redeploys, so the cache isn't
permanent across those events -- it still saves real money during each
period the app stays running, which covers the common case of many
people searching the same popular categories back to back. For a
permanent cache across restarts, this would need a small real database
instead of a local file -- a reasonable next upgrade once you have
actual usage to justify it.
"""

import os
import json
import re
import requests

CACHE_FILE = os.path.join(os.path.dirname(__file__), "checklist_cache.json")
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"  # cheap + fast, plenty for this task


def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # if disk isn't writable on some host, just skip persisting


def _normalize(query: str) -> str:
    return query.strip().lower()


def _call_claude(query: str) -> list:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it as an environment "
            "variable or Streamlit secret to use AI-generated checklists."
        )

    prompt = f"""A shopper in Tunisia is searching for: "{query}"

List the 5 most important features a non-expert should check when buying
this kind of product. For each feature, give:
- a short snake_case id
- a clear label a shopper would understand (in English)
- 2-4 keywords or short phrases (French and/or English) that would
  literally appear in a Tunisian e-commerce product description if that
  product has this feature -- these are used for exact substring
  matching against real scraped listings, so keep them concrete and
  specific (e.g. "22.5w", "bluetooth 5.3"), not vague marketing words.

Respond with ONLY a JSON array, nothing else, no markdown fences, no
explanation. Example shape:
[{{"id": "fast_charging", "label": "Fast charging", "keywords": ["22.5w", "22,5 w", "charge rapide"]}}]
"""

    resp = requests.post(
        API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": 800,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    text = "".join(
        block.get("text", "") for block in data.get("content", [])
        if block.get("type") == "text"
    )
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def get_or_generate_checklist(query: str) -> dict:
    """
    Returns a checklist dict shaped like: {id: {"label": ..., "check": fn}}
    where check(text) -> bool does a case-insensitive keyword match
    against a listing's combined name+description.

    Checks the disk cache first; only calls the API for genuinely new
    search terms. Returns {} on any failure (missing key, API error,
    bad JSON) so the app can gracefully fall back to price-only ranking
    instead of crashing.
    """
    cache = _load_cache()
    key = _normalize(query)

    if key not in cache:
        try:
            items = _call_claude(query)
            cache[key] = items
            _save_cache(cache)
        except Exception as e:
            print(f"[ai_checklist] generation failed for '{query}': {e}")
            return {}

    items = cache[key]
    checklist = {}
    for item in items:
        keywords = [kw.lower() for kw in item.get("keywords", [])]

        def make_check(kws):
            return lambda text: any(kw in text.lower() for kw in kws)

        checklist[item["id"]] = {
            "label": item["label"],
            "check": make_check(keywords),
        }
    return checklist


if __name__ == "__main__":
    # Quick manual test -- requires ANTHROPIC_API_KEY to actually be set
    result = get_or_generate_checklist("imprimante laser")
    for key, info in result.items():
        print(key, "->", info["label"])
