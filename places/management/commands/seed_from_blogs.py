"""
Seed the database from known Nigerian food blogs.

This replaces the entire auto-discovery Scrapy pipeline with a simple,
one-time management command. Run it to bootstrap initial candidates:

    python manage.py seed_from_blogs

It fetches articles from a handful of known blogs, extracts venue
information, and creates Candidates via the standard submission pipeline.
"""

import logging
import re
import time

import requests
from django.core.management.base import BaseCommand

from ingestion.extractors import extract_readable, extract_jsonld
from places.models import Submission, Candidate, PhotoURL
from places.nlp_utils import has_food_keywords, extract_phones_from_text, NIGERIAN_CITIES
from places.services import create_candidate_from_submission

logger = logging.getLogger(__name__)

# Known blog URLs likely to contain Amala spot articles
SEED_URLS = [
    # FoodieInLagos - known Amala review pages
    "https://foodieinlagos.com/?s=amala",
    # EatDrinkLagos
    "https://eatdrinklagos.com/?s=amala",
]

HEADERS = {
    'User-Agent': 'AmalaAtlas/1.0 Seed Script (contact@amalatlas.com)',
}


class Command(BaseCommand):
    help = "Seed the database with candidates from known Nigerian food blogs"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be created without actually creating records',
        )
        parser.add_argument(
            '--urls',
            nargs='+',
            help='Override seed URLs (space-separated)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        urls = options.get('urls') or SEED_URLS

        self.stdout.write(f"Seeding from {len(urls)} URLs (dry_run={dry_run})")

        created = 0
        skipped = 0

        for url in urls:
            self.stdout.write(f"\nFetching: {url}")
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as e:
                self.stderr.write(f"  Failed to fetch: {e}")
                continue

            html = resp.text
            readable = extract_readable(html)
            text = readable.get("text", "")
            title = readable.get("title", "")

            if not has_food_keywords(f"{title} {text}"):
                self.stdout.write(f"  Skipped (no food keywords)")
                skipped += 1
                continue

            # Try JSON-LD first (best structured data)
            jsonld = extract_jsonld(html)
            phones = extract_phones_from_text(text)

            # Detect city from text
            city = ""
            text_lower = text.lower()
            for c in NIGERIAN_CITIES:
                if c in text_lower:
                    city = c.title()
                    break

            name = ""
            address = ""
            phone = phones[0] if phones else ""

            if jsonld:
                name = jsonld.get("name", "") or title
                address = jsonld.get("address", "")
                phone = jsonld.get("telephone", "") or phone
            else:
                # Use title as name, extract what we can from text
                name = title if title else url.split("/")[-1].replace("-", " ").title()

            if not name:
                self.stdout.write(f"  Skipped (no name extracted)")
                skipped += 1
                continue

            self.stdout.write(f"  Found: {name} | {city} | {phone}")

            if dry_run:
                created += 1
                continue

            # Check if already exists
            if Candidate.objects.filter(name__iexact=name, city__iexact=city).exists():
                self.stdout.write(f"  Skipped (already exists)")
                skipped += 1
                continue

            submission = Submission.objects.create(
                name=name,
                kind="agentic",
                address=address,
                city=city,
                country="Nigeria",
                phone=phone,
                source_channel="seed_script",
                raw_payload={"source_url": url, "title": title},
            )

            candidate = create_candidate_from_submission(submission)
            created += 1
            self.stdout.write(self.style.SUCCESS(
                f"  Created candidate: {candidate.name} (score={candidate.score})"
            ))

            # Be polite to servers
            time.sleep(1)

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Created: {created}, Skipped: {skipped}"
        ))
