"""
Deduplication utilities salvaged from the auto-discovery service.

Nigerian Context:
- Same place: "Iya Toyin", "Mama Toyin", "Mama T"
- Phone numbers change frequently
- Addresses are informal and inconsistent
- No guaranteed unique identifiers

Strategy: phone exact match (strongest), then geohash + name similarity.
"""

import re
import logging
from difflib import SequenceMatcher
from typing import Optional

log = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """
    Normalize restaurant names for comparison.
    Strips common Nigerian prefixes, punctuation, extra whitespace.
    """
    if not name:
        return ""
    name = name.lower().strip()
    for prefix in ('iya ', 'mama ', 'buka ', 'mr ', 'mrs ', 'chef '):
        if name.startswith(prefix):
            name = name[len(prefix):]
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def normalize_phone(phone: str) -> Optional[str]:
    """
    Normalize Nigerian phone numbers to 11-digit format (0XXXXXXXXXX).
    Handles +234, spaces, dashes.
    """
    if not phone:
        return None
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('234') and len(digits) == 13:
        digits = '0' + digits[3:]
    elif digits.startswith('234') and len(digits) == 14:
        digits = digits[4:]
    if len(digits) == 11 and digits[0] == '0':
        return digits
    return None


def name_similarity(name1: str, name2: str) -> float:
    """Fuzzy name similarity (0.0 to 1.0) using SequenceMatcher."""
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    if not norm1 or not norm2:
        return 0.0
    return SequenceMatcher(None, norm1, norm2).ratio()


def make_dedupe_key(name: Optional[str], lat: Optional[float], lng: Optional[float], phone: Optional[str] = None) -> str:
    """
    Build a deduplication key for a candidate.

    Priority: phone (strongest), then geohash + normalized name.
    """
    phone_norm = normalize_phone(phone) if phone else None
    if phone_norm:
        return f"phone:{phone_norm}"

    name_norm = normalize_name(name or "")
    if lat is not None and lng is not None:
        # Simple grid: round to ~500m precision
        lat_bucket = round(lat, 3)
        lng_bucket = round(lng, 3)
        return f"geo:{lat_bucket},{lng_bucket}:{name_norm}"

    return f"name:{name_norm}"


def is_duplicate_of_existing(name, lat, lng, phone, queryset):
    """
    Check if a candidate duplicates any existing record in the queryset.

    Returns the matching record or None.
    """
    from places.models import Candidate

    # Check 1: Exact phone match (strongest signal)
    phone_norm = normalize_phone(phone) if phone else None
    if phone_norm:
        match = queryset.filter(dedupe_key=f"phone:{phone_norm}").first()
        if match:
            return match

    # Check 2: Same dedupe_key
    key = make_dedupe_key(name, lat, lng, phone)
    match = queryset.filter(dedupe_key=key).first()
    if match:
        return match

    # Check 3: Fuzzy name match in same city (if no coordinates)
    # This is more expensive so we only do it as a last resort
    name_norm = normalize_name(name or "")
    if name_norm and lat is not None and lng is not None:
        nearby = queryset.filter(
            lat__range=(lat - 0.01, lat + 0.01),  # ~1km
            lng__range=(lng - 0.01, lng + 0.01),
        )
        for candidate in nearby[:20]:
            if name_similarity(name, candidate.name) >= 0.85:
                return candidate

    return None
