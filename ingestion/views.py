"""
Ingestion endpoints for automated/agentic discovery services.

These endpoints accept candidate data from:
- Google Maps Places API agent
- Twitter/X monitoring agent
- Seed scraping script
- Any future automated discovery channel

Authentication: API key via X-API-Key header.
"""

import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from places.dedupe import is_duplicate_of_existing
from places.models import Submission, Candidate, PhotoURL
from places.services import create_candidate_from_submission

logger = logging.getLogger(__name__)

INGEST_API_KEY = getattr(settings, 'INGEST_API_KEY', 'dev-ingest-key')


def _check_api_key(request):
    """Validate the X-API-Key header."""
    key = request.headers.get('X-API-Key', '')
    return key == INGEST_API_KEY


class IngestCandidateView(APIView):
    """
    POST /ingest/
    Accepts a single candidate from an agentic discovery service.

    Request body:
    {
        "name": "Iya Basira Amala",
        "address": "Mokola roundabout",
        "city": "Ibadan",
        "state": "Oyo",
        "lat": 7.3975,
        "lng": 3.9170,
        "phone": "08031234567",
        "source_channel": "google_maps",
        "source_url": "https://maps.google.com/...",
        "evidence": [{"kind": "google_places", "rating": 4.5}],
        "photo_urls": ["https://..."],
        "tags": ["amala", "buka"],
        "price_band": "₦",
        "hours_text": "Mon-Sat 8am-8pm"
    }
    """

    def post(self, request):
        if not _check_api_key(request):
            return Response(
                {"error": "Invalid or missing API key"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        data = request.data
        name = data.get('name')
        if not name:
            return Response(
                {"error": "name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check for duplicates before creating
        existing = is_duplicate_of_existing(
            name=name,
            lat=data.get('lat'),
            lng=data.get('lng'),
            phone=data.get('phone'),
            queryset=Candidate.objects.exclude(status="rejected"),
        )
        if existing:
            return Response({
                "ok": True,
                "is_duplicate": True,
                "existing_candidate_id": str(existing.public_id),
                "message": f"Duplicate of existing candidate: {existing.name}",
            }, status=status.HTTP_200_OK)

        # Create Submission (audit trail)
        photo_urls = data.get('photo_urls', [])
        submission = Submission.objects.create(
            name=name,
            kind="agentic",
            address=data.get('address', ''),
            city=data.get('city', ''),
            state=data.get('state', ''),
            country=data.get('country', 'Nigeria'),
            lat=data.get('lat'),
            lng=data.get('lng'),
            phone=data.get('phone', ''),
            website=data.get('website', ''),
            email=data.get('email', ''),
            price_band=data.get('price_band', ''),
            tags=data.get('tags', []),
            hours_text=data.get('hours_text', ''),
            source_channel=data.get('source_channel', 'agent'),
            raw_payload=data,
        )

        for url in photo_urls:
            PhotoURL.objects.create(url=url, content_object=submission)

        candidate = create_candidate_from_submission(submission, photo_urls=photo_urls)

        return Response({
            "ok": True,
            "is_duplicate": False,
            "candidate_id": str(candidate.public_id),
            "score": float(candidate.score),
            "status": candidate.status,
        }, status=status.HTTP_201_CREATED)


class IngestBatchView(APIView):
    """
    POST /ingest/batch/
    Accepts multiple candidates at once.

    Request body:
    {
        "candidates": [
            {"name": "...", "city": "...", ...},
            {"name": "...", "city": "...", ...}
        ]
    }
    """

    def post(self, request):
        if not _check_api_key(request):
            return Response(
                {"error": "Invalid or missing API key"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        candidates_data = request.data.get('candidates', [])
        if not candidates_data:
            return Response(
                {"error": "candidates array is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = 0
        duplicates = 0
        errors = 0
        results = []

        for item in candidates_data:
            try:
                name = item.get('name')
                if not name:
                    errors += 1
                    results.append({"name": None, "error": "name is required"})
                    continue

                existing = is_duplicate_of_existing(
                    name=name,
                    lat=item.get('lat'),
                    lng=item.get('lng'),
                    phone=item.get('phone'),
                    queryset=Candidate.objects.exclude(status="rejected"),
                )
                if existing:
                    duplicates += 1
                    results.append({"name": name, "is_duplicate": True, "existing_id": str(existing.public_id)})
                    continue

                photo_urls = item.get('photo_urls', [])
                submission = Submission.objects.create(
                    name=name,
                    kind="agentic",
                    address=item.get('address', ''),
                    city=item.get('city', ''),
                    state=item.get('state', ''),
                    country=item.get('country', 'Nigeria'),
                    lat=item.get('lat'),
                    lng=item.get('lng'),
                    phone=item.get('phone', ''),
                    price_band=item.get('price_band', ''),
                    tags=item.get('tags', []),
                    hours_text=item.get('hours_text', ''),
                    source_channel=item.get('source_channel', 'agent'),
                    raw_payload=item,
                )

                for url in photo_urls:
                    PhotoURL.objects.create(url=url, content_object=submission)

                candidate = create_candidate_from_submission(submission, photo_urls=photo_urls)
                created += 1
                results.append({"name": name, "candidate_id": str(candidate.public_id), "score": float(candidate.score)})

            except Exception as e:
                errors += 1
                results.append({"name": item.get('name'), "error": str(e)})
                logger.exception(f"Error ingesting candidate: {item.get('name')}")

        return Response({
            "ok": True,
            "created": created,
            "duplicates": duplicates,
            "errors": errors,
            "results": results,
        }, status=status.HTTP_201_CREATED if created > 0 else status.HTTP_200_OK)
