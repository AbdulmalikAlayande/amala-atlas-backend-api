import logging
from typing import Dict, Any, Tuple, Optional

from places.models import Submission, Candidate, PhotoURL
from places.nlp_utils import FOOD_KEYWORDS, count_keyword_hits
from places.geocoding import geocode_address
from places.dedupe import make_dedupe_key, is_duplicate_of_existing

logger = logging.getLogger(__name__)


def geocode_if_needed(sub: Submission) -> Tuple[Optional[float], Optional[float], str]:
    """
    Resolve coordinates for a submission.

    If lat/lng already present (e.g. WhatsApp location pin), use them.
    Otherwise, try geocoding the address/city via Nominatim + city centroid fallback.
    """
    if sub.lat is not None and sub.lng is not None:
        return sub.lat, sub.lng, "address"

    result = geocode_address(address=sub.address, city=sub.city)
    if result:
        return result.lat, result.lng, result.precision

    return None, None, "city"


def compute_signals(sub: Submission) -> Dict[str, Any]:
    """Compute evidence signals from a submission."""
    text = f"{sub.name or ''} {sub.address or ''} {sub.city or ''}".lower()
    keyword_hits = count_keyword_hits(text, FOOD_KEYWORDS)

    return {
        "keyword_hits": keyword_hits,
        "has_photo": sub.photo_urls.exists(),
        "has_coords": sub.lat is not None and sub.lng is not None,
    }


def compute_score(signals: Dict[str, Any], source_channel: str = "web_form") -> float:
    """
    Compute confidence score (0.0 to 1.0) based on signals and source channel.

    Different channels carry different inherent trust levels:
    - google_maps: Already verified by Google's review system
    - whatsapp with coords: Person physically at the location
    - whatsapp text only: Person knows the spot but no GPS proof
    - web_form: Standard submission
    - twitter/seed_script: Lower confidence, needs more verification
    """
    score = 0.0

    # Base signal scoring
    score += 0.35 if signals.get("keyword_hits", 0) >= 1 else 0.0
    score += 0.10 if signals.get("has_photo") else 0.0
    score += 0.10 if signals.get("has_coords") else 0.0

    # Source channel trust bonuses
    if source_channel == "google_maps":
        score += 0.35
    elif source_channel == "whatsapp" and signals.get("has_coords"):
        score += 0.30
    elif source_channel == "whatsapp":
        score += 0.15
    elif source_channel == "web_form" and signals.get("has_photo"):
        score += 0.20
    elif source_channel == "web_form":
        score += 0.10
    elif source_channel == "twitter":
        score += 0.05
    elif source_channel == "seed_script":
        score += 0.10

    return max(0.0, min(1.0, score))


def create_candidate_from_submission(sub: Submission, photo_urls=None) -> Candidate:
    """
    Create a Candidate from a Submission.

    Handles geocoding, signal computation, scoring, deduplication, and photo association.
    """
    if photo_urls is None:
        photo_urls = []

    lat, lng, precision = geocode_if_needed(sub)
    signals = compute_signals(sub)
    source_channel = getattr(sub, 'source_channel', '') or 'web_form'
    score = compute_score(signals, source_channel)
    dedupe = make_dedupe_key(sub.name, lat, lng, sub.phone)

    # Check for duplicates before creating
    existing = is_duplicate_of_existing(
        name=sub.name, lat=lat, lng=lng, phone=sub.phone,
        queryset=Candidate.objects.exclude(status="rejected"),
    )
    if existing:
        logger.info(f"Duplicate found for '{sub.name}', existing candidate: {existing.id}")
        # Still create the candidate but link it as a duplicate
        # This preserves the evidence from the new source

    source_kind = "user" if sub.kind == "manual" else "agent"

    candidate = Candidate.objects.create(
        name=sub.name,
        raw_address=sub.address or "",
        city=sub.city,
        state=sub.state or "",
        country=sub.country or "Nigeria",
        lat=lat,
        lng=lng,
        tags=sub.tags,
        hours_text = sub.hours_text,
        phone = sub.phone or "Not Available",
        website = sub.website or "Not Available",
        email = sub.email or "Not Available",
        price_band=sub.price_band or "",
        source_url="",
        source_kind="user",
        evidence=[{"kind": "user_submit", "photo_url": [{"url": photo_url.url} for photo_url in sub.photo_urls.all()]}] if sub.photo_urls.exists() else [],
        signals=signals,
        score=score,
        dedupe_key=make_dedupe_key(sub.name, lat, lng),
        geo_precision=precision,
        status="pending_verification",
    )

    if not sub.photo_urls.exists() or sub.photo_urls.count() > 0:
        for url in photo_urls:
            PhotoURL.objects.create(url=url, content_object=candidate)

    return candidate