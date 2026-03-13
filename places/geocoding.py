"""
Geocoding service salvaged from the auto-discovery service.

Strategy:
1. Try full address via Nominatim (OpenStreetMap)
2. Fallback to city-level Nominatim
3. Fallback to hardcoded Nigerian city centroids
4. Never fail - always return something if city is known
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests

log = logging.getLogger(__name__)

# Nigerian city centroids (fallback when geocoding fails)
CITY_CENTROIDS = {
    'lagos': (6.5244, 3.3792),
    'ibadan': (7.3775, 3.9470),
    'abuja': (9.0765, 7.3986),
    'port harcourt': (4.8156, 7.0498),
    'kano': (12.0022, 8.5919),
    'abeokuta': (7.1475, 3.3619),
    'ilorin': (8.4966, 4.5426),
    'oshogbo': (7.7667, 4.5667),
    'ikeja': (6.6018, 3.3515),
    'surulere': (6.5027, 3.3597),
    'yaba': (6.5158, 3.3704),
    'victoria island': (6.4281, 3.4219),
    'lekki': (6.4474, 3.5617),
    'ikorodu': (6.6194, 3.5105),
}

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {'User-Agent': 'AmalaAtlas/1.0 (contact@amalatlas.com)'}
_last_request_time = 0


@dataclass
class GeocodingResult:
    lat: float
    lng: float
    precision: str  # exact|street|neighborhood|city|city_centroid
    source: str     # nominatim|nominatim_city|fallback


def _rate_limit():
    """Enforce 1 request/second for Nominatim policy."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _last_request_time = time.time()


def _geocode_nominatim(query: str) -> Optional[GeocodingResult]:
    """Query Nominatim and return result."""
    _rate_limit()
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={'q': query, 'format': 'json', 'limit': 1, 'addressdetails': 1},
            headers=NOMINATIM_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None

        r = results[0]
        lat, lng = float(r['lat']), float(r['lon'])
        addr = r.get('address', {})

        if addr.get('house_number'):
            precision = "exact"
        elif r.get('type') in ('road', 'residential'):
            precision = "street"
        elif r.get('type') in ('suburb', 'neighbourhood'):
            precision = "neighborhood"
        else:
            precision = "city"

        return GeocodingResult(lat=lat, lng=lng, precision=precision, source="nominatim")
    except Exception as e:
        log.warning(f"Nominatim failed for '{query}': {e}")
        return None


def geocode_address(address: Optional[str], city: Optional[str], country: str = "Nigeria") -> Optional[GeocodingResult]:
    """
    Geocode with fallback strategy.

    1. Full address + city + country via Nominatim
    2. City + country via Nominatim
    3. Hardcoded city centroid
    """
    # Strategy 1: Full address
    if address:
        parts = [p for p in [address, city, country] if p]
        result = _geocode_nominatim(", ".join(parts))
        if result:
            return result

    # Strategy 2: City-level Nominatim
    if city:
        result = _geocode_nominatim(f"{city}, {country}")
        if result:
            result.precision = "city"
            result.source = "nominatim_city"
            return result

    # Strategy 3: Hardcoded centroid
    if city:
        city_lower = city.lower().strip()
        if city_lower in CITY_CENTROIDS:
            lat, lng = CITY_CENTROIDS[city_lower]
            return GeocodingResult(lat=lat, lng=lng, precision="city_centroid", source="fallback")

    return None
