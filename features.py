"""
Pulls structured features out of raw product description text, so the
checkbox-matching feature has something concrete to check against.

Built and tuned against REAL scraped Tunisianet power bank descriptions
(see the sample output that led to this file), not guessed.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductFeatures:
    max_watts: Optional[float]
    max_mah: Optional[int]
    has_usb_c: bool
    is_multi_port: bool      # can charge 2+ devices at once
    has_protection: bool     # overcharge/short-circuit/surge protection mentioned
    has_included_cable: bool


def extract_features(description: str) -> ProductFeatures:
    text = description.lower()

    # Wattage: matches "22,5 w", "18.5w", "20 w" etc. Takes the highest
    # number found, since some descriptions list both input and output watts.
    watt_matches = re.findall(r"(\d+[.,]?\d*)\s*w\b", text)
    watts = [float(w.replace(",", ".")) for w in watt_matches] if watt_matches else []
    max_watts = max(watts) if watts else None

    # Capacity: matches "10000 mah", "20 000 mah" (with space as thousands
    # separator, common in French formatting).
    mah_matches = re.findall(r"(\d[\d\s]{2,6})\s*mah", text)
    mah_values = [int(m.replace(" ", "")) for m in mah_matches] if mah_matches else []
    max_mah = max(mah_values) if mah_values else None

    has_usb_c = "usb-c" in text or "type-c" in text or "type c" in text

    # Multi-port / simultaneous charging: look for "2x usb", "3 x usb",
    # or explicit phrases like "chargez ... appareils" (charge N devices).
    port_count_match = re.search(r"(\d)\s*x\s*usb", text)
    simultaneous_phrase = "simultan" in text or "à la fois" in text
    is_multi_port = bool(port_count_match and int(port_count_match.group(1)) >= 2) or simultaneous_phrase

    protection_keywords = ["protection", "surcharge", "surtension", "court-circuit", "multiprotect"]
    has_protection = any(k in text for k in protection_keywords)

    cable_keywords = ["câble intégré", "câbles intégrés", "avec câble", "cable inclus", "câble inclus"]
    has_included_cable = any(k in text for k in cable_keywords)

    return ProductFeatures(
        max_watts=max_watts,
        max_mah=max_mah,
        has_usb_c=has_usb_c,
        is_multi_port=is_multi_port,
        has_protection=has_protection,
        has_included_cable=has_included_cable,
    )


# The checklist shown to the user as "6 boxes to check". Each entry maps
# a friendly label to a function that checks ProductFeatures and returns
# True/False for whether that listing satisfies it.
CHECKLIST = {
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
}


if __name__ == "__main__":
    # Quick sanity check against a couple of the real descriptions we saw
    samples = [
        "Power Bank Intenso XS10000 - Capacité: 10 000 mAh - Connecteurs: 1x Micro-USB, 1x USB-C, 1x USB-A - Protection contre les surtensions - Protection contre les surcharges - Protection contre les courts-circuits",
        "Power Bank RIVAVASE VA2311 - Capacité de la batterie : 10000 mAh / 37 Wh - Port : 2x USB-C, 1x USB-A - Recharge simultanée de deux appareils : 22.5 W",
    ]
    for s in samples:
        feats = extract_features(s)
        print(feats)
        matched = [k for k, v in CHECKLIST.items() if v["check"](feats)]
        print("  matches:", matched)
