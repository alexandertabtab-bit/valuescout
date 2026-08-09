"""
Pulls structured features out of raw product description text, and
picks the right checklist depending on what category the search term
looks like it belongs to -- so "casque bluetooth" shows headphone-
relevant checkboxes, not power bank ones.

Built and tuned against REAL scraped Tunisianet descriptions.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductFeatures:
    max_watts: Optional[float]
    max_mah: Optional[int]
    max_battery_hours: Optional[float]
    max_dpi: Optional[int]
    has_usb_c: bool
    is_multi_port: bool
    has_protection: bool
    has_included_cable: bool
    has_bluetooth: bool
    is_wireless: bool
    has_noise_cancelling: bool
    has_microphone: bool
    has_rgb: bool
    is_water_resistant: bool


def extract_features(description: str) -> ProductFeatures:
    text = description.lower()

    watt_matches = re.findall(r"(\d+[.,]?\d*)\s*w\b", text)
    watts = [float(w.replace(",", ".")) for w in watt_matches] if watt_matches else []
    max_watts = max(watts) if watts else None

    mah_matches = re.findall(r"(\d[\d\s]{2,6})\s*mah", text)
    mah_values = [int(m.replace(" ", "")) for m in mah_matches] if mah_matches else []
    max_mah = max(mah_values) if mah_values else None

    # Battery life in hours, e.g. "autonomie: 40 heures" or "40 heures d'autonomie"
    hour_matches = re.findall(r"(\d+[.,]?\d*)\s*heures?\b", text)
    hours = [float(h.replace(",", ".")) for h in hour_matches] if hour_matches else []
    max_battery_hours = max(hours) if hours else None

    dpi_matches = re.findall(r"(\d{3,5})\s*dpi", text)
    dpi_values = [int(d) for d in dpi_matches] if dpi_matches else []
    max_dpi = max(dpi_values) if dpi_values else None

    has_usb_c = "usb-c" in text or "type-c" in text or "type c" in text

    port_count_match = re.search(r"(\d)\s*x\s*usb", text)
    simultaneous_phrase = "simultan" in text or "à la fois" in text
    is_multi_port = bool(port_count_match and int(port_count_match.group(1)) >= 2) or simultaneous_phrase

    protection_keywords = ["protection", "surcharge", "surtension", "court-circuit", "multiprotect"]
    has_protection = any(k in text for k in protection_keywords)

    cable_keywords = ["câble intégré", "câbles intégrés", "avec câble", "cable inclus", "câble inclus"]
    has_included_cable = any(k in text for k in cable_keywords)

    has_bluetooth = "bluetooth" in text
    is_wireless = has_bluetooth or "sans fil" in text or "wireless" in text

    noise_cancel_keywords = ["réduction du bruit", "anc", "noise cancel", "suppression du bruit"]
    has_noise_cancelling = any(k in text for k in noise_cancel_keywords)

    mic_keywords = ["microphone", "avec micro", "casque-micro", "casque micro"]
    has_microphone = any(k in text for k in mic_keywords)

    has_rgb = "rgb" in text

    water_keywords = ["ipx", "étanche", "résistance à l'eau", "resistance a l'eau", "waterproof"]
    is_water_resistant = any(k in text for k in water_keywords)

    return ProductFeatures(
        max_watts=max_watts,
        max_mah=max_mah,
        max_battery_hours=max_battery_hours,
        max_dpi=max_dpi,
        has_usb_c=has_usb_c,
        is_multi_port=is_multi_port,
        has_protection=has_protection,
        has_included_cable=has_included_cable,
        has_bluetooth=has_bluetooth,
        is_wireless=is_wireless,
        has_noise_cancelling=has_noise_cancelling,
        has_microphone=has_microphone,
        has_rgb=has_rgb,
        is_water_resistant=is_water_resistant,
    )


# Per-category checklists. Each entry maps a friendly label to a
# function that checks ProductFeatures and returns True/False.
CATEGORY_CHECKLISTS = {
    "power_bank": {
        "fast_charging": {
            "label": "Fast charging (18W or more)",
            "check": lambda f: f.max_watts is not None and f.max_watts >= 18,
        },
        "high_capacity": {
            "label": "High capacity (20,000mAh or more)",
            "check": lambda f: f.max_mah is not None and f.max_mah >= 20000,
        },
        "multi_device": {
            "label": "Can charge multiple devices at once",
            "check": lambda f: f.is_multi_port,
        },
        "usb_c": {
            "label": "USB-C support",
            "check": lambda f: f.has_usb_c,
        },
        "safety_protection": {
            "label": "Overcharge / short-circuit protection",
            "check": lambda f: f.has_protection,
        },
        "included_cable": {
            "label": "Comes with a built-in/included cable",
            "check": lambda f: f.has_included_cable,
        },
    },
    "casque": {
        "bluetooth": {
            "label": "Bluetooth / wireless",
            "check": lambda f: f.has_bluetooth,
        },
        "noise_cancelling": {
            "label": "Noise cancelling",
            "check": lambda f: f.has_noise_cancelling,
        },
        "microphone": {
            "label": "Built-in microphone",
            "check": lambda f: f.has_microphone,
        },
        "long_battery": {
            "label": "Long battery life (20+ hours)",
            "check": lambda f: f.max_battery_hours is not None and f.max_battery_hours >= 20,
        },
        "water_resistant": {
            "label": "Water/sweat resistant",
            "check": lambda f: f.is_water_resistant,
        },
    },
    "souris": {
        "wireless": {
            "label": "Wireless",
            "check": lambda f: f.is_wireless,
        },
        "rgb": {
            "label": "RGB lighting",
            "check": lambda f: f.has_rgb,
        },
        "high_dpi": {
            "label": "High precision (8000+ DPI)",
            "check": lambda f: f.max_dpi is not None and f.max_dpi >= 8000,
        },
        "usb_c_charging": {
            "label": "USB-C charging",
            "check": lambda f: f.has_usb_c,
        },
    },
}

# Keywords used to detect which category a search term belongs to.
# Add more (category_key: [keywords...]) as you support more categories.
CATEGORY_DETECTION = {
    "power_bank": ["power bank", "powerbank"],
    "casque": ["casque", "écouteur", "ecouteur", "earphone", "headphone", "airpods", "écouteurs"],
    "souris": ["souris", "mouse"],
}


def detect_category(query: str) -> Optional[str]:
    """
    Guesses which checklist to show based on the search term. Returns
    None if the term doesn't match any known category -- in that case,
    the app should fall back to price-only ranking with no checkboxes.
    """
    q = query.lower().strip()
    for category, keywords in CATEGORY_DETECTION.items():
        if any(k in q for k in keywords):
            return category
    return None


def get_checklist(category: Optional[str]) -> dict:
    """Returns the checklist dict for a category, or empty dict if unknown."""
    if category is None:
        return {}
    return CATEGORY_CHECKLISTS.get(category, {})


if __name__ == "__main__":
    # Sanity checks against real descriptions from different categories
    samples = [
        ("power bank", "Power Bank RIVAVASE VA2311 - Capacité de la batterie : 10000 mAh / 37 Wh - Port : 2x USB-C, 1x USB-A - Recharge simultanée de deux appareils : 22.5 W"),
        ("casque bluetooth", "Casque Bluetooth Hama Spirit Calypso II - Connexion: Bluetooth 5.3 - Autonomie max en communication: 60 heures - Microphone intégré - Type de charge: USB-C"),
    ]
    for query, desc in samples:
        cat = detect_category(query)
        checklist = get_checklist(cat)
        feats = extract_features(desc)
        matched = [k for k, v in checklist.items() if v["check"](feats)]
        print(f"query='{query}' -> category='{cat}' -> matched={matched}")
