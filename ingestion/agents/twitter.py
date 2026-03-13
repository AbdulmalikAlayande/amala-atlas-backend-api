"""
Twitter/X monitoring agent.

Searches Twitter for Amala spot mentions and creates candidates
from tweets that reference specific venues.

Requires: TWITTER_BEARER_TOKEN in environment/settings.

Usage:
    python manage.py run_twitter_scan
    # Or via Celery task: scan_twitter.delay()
"""

import logging
import re

from django.conf import settings

from places.dedupe import is_duplicate_of_existing
from places.models import Submission, Candidate
from places.nlp_utils import NIGERIAN_CITIES, extract_phones_from_text
from places.services import create_candidate_from_submission

logger = logging.getLogger(__name__)

TWITTER_BEARER_TOKEN = getattr(settings, 'TWITTER_BEARER_TOKEN', '')

# Twitter search queries designed to find venue mentions, not recipes
SEARCH_QUERIES = [
    '"amala" (spot OR joint OR buka OR restaurant) (lagos OR ibadan OR abuja OR abeokuta) -recipe -cook -how',
    '"amala spot" OR "amala joint" OR "amala buka" -recipe',
    '"best amala" (lagos OR ibadan) -recipe -make',
]


def scan_twitter() -> dict:
    """
    Search Twitter for Amala spot mentions.

    Returns: {created: int, duplicates: int, skipped: int, errors: int, total: int}
    """
    if not TWITTER_BEARER_TOKEN:
        logger.error("TWITTER_BEARER_TOKEN not configured")
        return {"created": 0, "duplicates": 0, "skipped": 0, "errors": 0, "total": 0, "error": "Token not configured"}

    try:
        import tweepy
    except ImportError:
        logger.error("tweepy package not installed. Run: pip install tweepy")
        return {"created": 0, "duplicates": 0, "skipped": 0, "errors": 0, "total": 0, "error": "tweepy not installed"}

    client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)

    created = 0
    duplicates_count = 0
    skipped = 0
    errors = 0
    total = 0

    for query in SEARCH_QUERIES:
        logger.info(f"Searching Twitter: '{query[:60]}...'")

        try:
            response = client.search_recent_tweets(
                query=query,
                max_results=50,
                tweet_fields=['created_at', 'author_id', 'geo'],
            )
        except Exception as e:
            logger.error(f"Twitter API error: {e}")
            errors += 1
            continue

        if not response.data:
            continue

        for tweet in response.data:
            total += 1
            try:
                result = _process_tweet(tweet)
                if result == "created":
                    created += 1
                elif result == "duplicate":
                    duplicates_count += 1
                elif result == "skipped":
                    skipped += 1
            except Exception as e:
                logger.exception(f"Error processing tweet {tweet.id}: {e}")
                errors += 1

    logger.info(f"Twitter scan: total={total}, created={created}, duplicates={duplicates_count}, skipped={skipped}")
    return {"created": created, "duplicates": duplicates_count, "skipped": skipped, "errors": errors, "total": total}


def _process_tweet(tweet) -> str:
    """
    Extract venue data from a tweet and create a candidate.

    Returns: "created" | "duplicate" | "skipped"
    """
    text = tweet.text

    # Try to extract a venue name — look for patterns like "at X" or quoted names
    venue = _extract_venue_name(text)
    if not venue:
        return "skipped"

    # Detect city
    city = _detect_city(text)
    if not city:
        return "skipped"

    # Extract phone if mentioned
    phones = extract_phones_from_text(text)
    phone = phones[0] if phones else ""

    # Check for duplicates
    existing = is_duplicate_of_existing(
        name=venue, lat=None, lng=None, phone=phone,
        queryset=Candidate.objects.exclude(status="rejected"),
    )
    if existing:
        return "duplicate"

    submission = Submission.objects.create(
        name=venue,
        kind="agentic",
        city=city,
        country="Nigeria",
        phone=phone,
        source_channel="twitter",
        raw_payload={
            "tweet_id": str(tweet.id),
            "tweet_text": text,
            "created_at": str(tweet.created_at) if tweet.created_at else "",
        },
    )

    create_candidate_from_submission(submission)
    return "created"


def _extract_venue_name(text: str) -> str | None:
    """
    Try to extract a venue name from tweet text.

    Patterns:
    - "at Iya Toyin's"
    - "Mama Cass in Surulere"
    - quoted names: "Amala Skoto"
    """
    # Pattern 1: "at <Name>" (2-4 capitalized words after "at")
    match = re.search(r'\bat\s+([A-Z][a-zA-Z\']+(?:\s+[A-Z][a-zA-Z\']+){0,3})', text)
    if match:
        return match.group(1).strip()

    # Pattern 2: Names with Iya/Mama prefix
    match = re.search(r'((?:Iya|Mama|Buka)\s+[A-Z][a-zA-Z\']+(?:\s+[A-Z][a-zA-Z\']+)?)', text)
    if match:
        return match.group(1).strip()

    # Pattern 3: Quoted venue names
    match = re.search(r'["""]([^"""]{3,40})["""]', text)
    if match:
        return match.group(1).strip()

    return None


def _detect_city(text: str) -> str | None:
    """Detect Nigerian city from tweet text."""
    text_lower = text.lower()
    for city in sorted(NIGERIAN_CITIES, key=len, reverse=True):
        if city in text_lower:
            return city.title()
    return None
