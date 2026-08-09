"""
ValueScout -- Streamlit app

A search box (well, category picker for now) + checkboxes for what you
care about + a ranked results table with the sweet spot highlighted.

Run locally with:  streamlit run app.py
"""

import streamlit as st
from statistics import median, mean

from scrapers.tunisianet import search_tunisianet
from features import get_checklist, detect_category, extract_features


st.set_page_config(page_title="ValueScout", page_icon="🔎", layout="centered")

st.title("🔎 ValueScout")
st.caption("Find the price/quality sweet spot, not just the cheapest or the priciest.")

# --- Inputs ---
query = st.text_input(
    "What are you looking for?",
    placeholder="e.g. power bank, casque bluetooth, souris gamer...",
    help="Searches Tunisianet directly -- try French or English terms.",
)

# The checklist shown depends on what category the search term looks
# like -- "casque bluetooth" shows headphone checkboxes, "souris"
# shows mouse checkboxes, etc. See features.py CATEGORY_DETECTION.
detected_category = detect_category(query) if query else None
checklist = get_checklist(detected_category)

selected_features = []
if checklist:
    st.write(f"What matters to you? (detected: {detected_category.replace('_', ' ')})")
    cols = st.columns(2)
    checklist_items = list(checklist.items())
    for i, (key, info) in enumerate(checklist_items):
        col = cols[i % 2]
        if col.checkbox(info["label"], key=f"chk_{detected_category}_{key}"):
            selected_features.append(key)
elif query:
    st.caption("No specific checklist for this yet -- ranking by price positioning only.")

search_clicked = st.button("Find the sweet spot", type="primary")


# --- Cached scraping so repeated clicks don't hammer the site ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_listings(query: str):
    return search_tunisianet(query, max_results=50)


def score_listings(listings, selected_features, checklist):
    WEIGHT_PRICE = 0.5
    WEIGHT_FEATURES = 0.5

    if not listings:
        return []

    prices = [l.price_tnd for l in listings]
    med = median(prices)
    price_range = max(prices) - min(prices) or 1
    min_price = min(prices)

    scored = []
    for l in listings:
        matched = []
        if selected_features:
            price_score = 1 - ((l.price_tnd - min_price) / price_range)
            feats = extract_features(f"{l.name} {l.description}")
            for key in selected_features:
                if checklist[key]["check"](feats):
                    matched.append(key)
            feature_score = len(matched) / len(selected_features)
            value_score = WEIGHT_PRICE * price_score + WEIGHT_FEATURES * feature_score
        else:
            distance_from_median = abs(l.price_tnd - med) / price_range
            value_score = 1 - distance_from_median

        scored.append({
            "listing": l,
            "value_score": round(value_score, 3),
            "matched": matched,
        })

    return sorted(scored, key=lambda x: x["value_score"], reverse=True)


# --- Run search + show results ---
if search_clicked:
    if not query.strip():
        st.warning("Type something to search for first.")
    else:
        with st.spinner(f"Searching Tunisianet for '{query}'..."):
            listings = get_listings(query)

        if not listings:
            st.error(
                f"No listings found for '{query}'. Try a different term, "
                f"or Tunisianet's page structure may have changed."
            )
        else:
            scored = score_listings(listings, selected_features, checklist)
            prices = [l.price_tnd for l in listings]

            st.success(f"Found {len(listings)} listings")
            st.caption(
                f"Price range: {min(prices):.3f} - {max(prices):.3f} DT | "
                f"Median: {median(prices):.3f} DT | Mean: {mean(prices):.3f} DT"
            )

            for i, entry in enumerate(scored):
                l = entry["listing"]
                is_top = i == 0
                with st.container(border=True):
                    if is_top:
                        st.markdown("**🏆 Sweet spot**")
                    cols = st.columns([3, 1])
                    cols[0].markdown(f"**[{l.name}]({l.url})**")
                    cols[0].caption(l.description)
                    cols[1].metric("Price", f"{l.price_tnd:.3f} DT")
                    if selected_features:
                        matched_labels = [checklist[k]["label"] for k in entry["matched"]]
                        st.caption(
                            f"Score: {entry['value_score']:.2f}  |  "
                            f"Matched {len(entry['matched'])}/{len(selected_features)}: "
                            f"{', '.join(matched_labels) if matched_labels else 'none'}"
                        )
                    else:
                        st.caption(f"Score: {entry['value_score']:.2f} (price positioning only)")
else:
    st.info("Type what you're looking for, check what matters to you, then click the button.")
