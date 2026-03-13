"""
NLP utilities salvaged from the auto-discovery service.

Provides keyword lists and simple text analysis for scoring
candidate submissions. No heavy NLP libraries needed.
"""

import re

# Core food keywords - Yoruba dishes and dining terms
FOOD_KEYWORDS = {
    'amala', 'abula', 'ewedu', 'gbegiri', 'ila', 'ogunfe',
    'buka', 'mama put', 'iya', 'mama', 'joint', 'spot',
    'canteen', 'kitchen', 'restaurant', 'eatery', 'cafe',
}

# Context keywords that indicate a real venue (not a recipe)
VENUE_KEYWORDS = {
    'location', 'address', 'phone', 'call', 'visit', 'located',
    'street', 'road', 'avenue', 'close', 'way', 'junction',
    'opposite', 'beside', 'near', 'behind', 'inside',
    'open', 'hours', 'monday', 'tuesday', 'wednesday', 'thursday',
    'friday', 'saturday', 'sunday', 'daily', 'weekday', 'weekend',
}

# Nigerian city names for location context
NIGERIAN_CITIES = {
    'lagos', 'ibadan', 'abuja', 'port harcourt', 'kano',
    'abeokuta', 'ilorin', 'oshogbo', 'ogbomosho', 'ile-ife',
    'akure', 'benin', 'enugu', 'oyo', 'ikeja', 'surulere',
    'yaba', 'victoria island', 'lekki', 'ikorodu', 'agege',
}

# Nigerian phone number patterns
PHONE_PATTERNS = [
    r'\b0[7-9]\d{9}\b',
    r'\+234\d{10}',
]


def count_keyword_hits(text, keywords):
    """Count how many keywords from a set appear in text."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower)


def has_food_keywords(text):
    """Check if text contains any food-related keywords."""
    return count_keyword_hits(text, FOOD_KEYWORDS) > 0


def extract_phones_from_text(text):
    """Extract Nigerian phone numbers from text."""
    phones = []
    for pattern in PHONE_PATTERNS:
        phones.extend(re.findall(pattern, text))
    return phones
