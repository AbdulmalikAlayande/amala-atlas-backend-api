"""
Google Maps Places API agent.

Searches for Amala spots in Nigerian cities using the Places API,
deduplicates against existing candidates, and ingests new ones.

Requires: GOOGLE_MAPS_API_KEY in environment/settings.

Usage:
    python manage.py run_google_maps_scan --city Lagos
    # Or via Celery task: scan_google_maps.delay("Lagos")
"""

import logging

from django.conf import settings

from places.dedupe import is_duplicate_of_existing
from places.geocoding import CITY_CENTROIDS
from places.models import Submission, Candidate, PhotoURL
from places.services import create_candidate_from_submission

logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')

# Search queries to run for each city
SEARCH_QUERIES = [
    "amala restaurant",
    "amala joint",
    "amala buka",
    "amala spot",
    "abula restaurant",
    "ewedu gbegiri",
]


def scan_google_maps(city: str) -> dict:
    """
    Search Google Maps for amala spots in a given city.

    Returns: {created: int, duplicates: int, errors: int, total: int}
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.error("GOOGLE_MAPS_API_KEY not configured")
        return {"created": 0, "duplicates": 0, "errors": 0, "total": 0, "error": "API key not configured"}

    try:
        import googlemaps
    except ImportError:
        logger.error("googlemaps package not installed. Run: pip install googlemaps")
        return {"created": 0, "duplicates": 0, "errors": 0, "total": 0, "error": "googlemaps not installed"}

    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

    city_lower = city.lower()
    centroid = CITY_CENTROIDS.get(city_lower)
    location = f"{centroid[0]},{centroid[1]}" if centroid else None

    created = 0
    duplicates = 0
    errors = 0
    total = 0

    for query in SEARCH_QUERIES:
        search_query = f"{query} {city}"
        logger.info(f"Searching Google Maps: '{search_query}'")

        try:
            results = gmaps.places(
                query=search_query,
                location=location,
                radius=25000,  # 25km
            )
        except Exception as e:
            logger.error(f"Google Maps API error for '{search_query}': {e}")
            errors += 1
            continue

        for place in results.get('results', []):
            total += 1
            try:
                result = _process_place(place, city)
                if result == "created":
                    created += 1
                elif result == "duplicate":
                    duplicates += 1
            except Exception as e:
                logger.exception(f"Error processing place {place.get('name')}: {e}")
                errors += 1

    logger.info(f"Google Maps scan for {city}: total={total}, created={created}, duplicates={duplicates}, errors={errors}")
    return {"created": created, "duplicates": duplicates, "errors": errors, "total": total}


def _process_place(place: dict, city: str) -> str:
    """
    Process a single Google Maps place result.

    Returns: "created" | "duplicate" | "skipped"
    """
    name = place.get('name', '')
    lat = place.get('geometry', {}).get('location', {}).get('lat')
    lng = place.get('geometry', {}).get('location', {}).get('lng')
    address = place.get('formatted_address', '') or place.get('vicinity', '')
    rating = place.get('rating', 0)
    user_ratings_total = place.get('user_ratings_total', 0)
    place_id = place.get('place_id', '')

    if not name:
        return "skipped"

    # Check for duplicates
    existing = is_duplicate_of_existing(
        name=name, lat=lat, lng=lng, phone=None,
        queryset=Candidate.objects.exclude(status="rejected"),
    )
    if existing:
        return "duplicate"

    # Create submission
    photo_urls = []
    if place.get('photos'):
        # Google Maps photo references (would need Places Photo API to resolve)
        # For now, store the reference
        pass

    submission = Submission.objects.create(
        name=name,
        kind="agentic",
        address=address,
        city=city,
        country="Nigeria",
        lat=lat,
        lng=lng,
        source_channel="google_maps",
        raw_payload={
            "place_id": place_id,
            "rating": rating,
            "user_ratings_total": user_ratings_total,
            "types": place.get('types', []),
            "business_status": place.get('business_status', ''),
        },
    )

    candidate = create_candidate_from_submission(submission)

    # Auto-verify high-confidence Google Maps results
    if rating >= 4.0 and user_ratings_total >= 10:
        _auto_verify(candidate)

    return "created"


def _auto_verify(candidate: Candidate):
    """Auto-promote high-confidence Google Maps candidates to Spots."""
    from places.models import Spot

    Spot.objects.create(
        name=candidate.name,
        lat=candidate.lat or 0.0,
        lng=candidate.lng or 0.0,
        address=candidate.raw_address or "",
        city=candidate.city,
        state=candidate.state,
        country=candidate.country,
        tags=candidate.tags or [],
        phone=candidate.phone or "",
        source="google_maps_auto",
    )
    candidate.status = "approved"
    candidate.save(update_fields=["status"])
    logger.info(f"Auto-verified Google Maps candidate: {candidate.name}")
