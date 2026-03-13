"""
Message parser for WhatsApp spot submissions.

Extracts structured data from informal Nigerian text messages.
No AI/LLM needed — patterns are predictable:
  "Iya Basira, Mokola Ibadan"
  "Mama T at Agege"
  "Amala spot in Surulere, behind the market"
"""

import re
from typing import Dict, Optional

from places.nlp_utils import NIGERIAN_CITIES, extract_phones_from_text


def parse_spot_message(text: str) -> Dict:
    """
    Parse a WhatsApp message to extract spot name and location.

    Returns:
        {
            "name": str or None,
            "city": str or None,
            "address": str or None,
            "phone": str or None,
            "parsed": bool (whether parsing succeeded)
        }
    """
    text = text.strip()
    if not text:
        return {"name": None, "city": None, "address": None, "phone": None, "parsed": False}

    # Extract phone numbers first (remove from text for cleaner parsing)
    phones = extract_phones_from_text(text)
    phone = phones[0] if phones else None

    # Try to split name from location using common separators
    name = None
    location = None

    # Pattern: "Name at/in Location"
    for sep in (r'\s+at\s+', r'\s+in\s+', r'\s*,\s*', r'\s*-\s+', r'\s+near\s+', r'\s+opposite\s+'):
        parts = re.split(sep, text, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2 and len(parts[0].strip()) > 1:
            name = parts[0].strip()
            location = parts[1].strip()
            break

    # If no separator found, treat the whole message as the name
    if name is None:
        name = text

    # Detect city from location text or full text
    city = _detect_city(location or text)

    # If location contains city, the rest might be address detail
    address = location if location else None

    return {
        "name": _clean_name(name),
        "city": city,
        "address": address,
        "phone": phone,
        "parsed": bool(name),
    }


def parse_location_text(text: str) -> Dict:
    """
    Parse a follow-up location message (when bot asks for location).

    Returns: {"city": str or None, "address": str or None}
    """
    text = text.strip()
    city = _detect_city(text)
    return {"city": city, "address": text if text else None}


def parse_extras_message(text: str) -> Dict:
    """
    Parse optional extras (phone, price, etc.) from a follow-up message.

    Returns: dict of extracted fields
    """
    text = text.strip().lower()
    result = {}

    # Check for phone
    phones = extract_phones_from_text(text)
    if phones:
        result["phone"] = phones[0]

    # Check for price indicators
    if any(w in text for w in ("cheap", "₦", "affordable", "budget")):
        result["price_band"] = "₦"
    elif any(w in text for w in ("mid", "moderate", "average")):
        result["price_band"] = "₦₦"
    elif any(w in text for w in ("expensive", "pricey", "upscale")):
        result["price_band"] = "₦₦₦"

    return result


def _detect_city(text: str) -> Optional[str]:
    """Detect a Nigerian city name in text."""
    text_lower = text.lower()
    for city in sorted(NIGERIAN_CITIES, key=len, reverse=True):
        if city in text_lower:
            return city.title()
    return None


def _clean_name(name: str) -> str:
    """Clean up a spot name extracted from a message."""
    # Remove trailing punctuation
    name = re.sub(r'[.,!?;:]+$', '', name).strip()
    # Capitalize words
    return name.title() if name.islower() else name
