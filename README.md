# Amala Atlas — Backend API

[![Django](https://img.shields.io/badge/Django-5.2+-092e20.svg)](https://www.djangoproject.com)
[![DRF](https://img.shields.io/badge/DRF-3.14+-red.svg)](https://www.django-rest-framework.org)
[![Live](https://img.shields.io/badge/API-amala--atlas.onrender.com-blue.svg)](https://amala-atlas.onrender.com)

The **system of record** for the Amala Atlas ecosystem. Manages the full lifecycle of an Amala spot — from raw submission through scoring, deduplication, verification, and promotion to the canonical map database.

## Architecture

The backend is a Django project with six apps, each handling a distinct domain:

```
amala_atlas/                # Django project config (settings, urls, wsgi)
├── places/                 # Core: Spot, Candidate, Submission, PhotoURL
│   ├── models.py           # Data models
│   ├── services.py         # Scoring, geocoding integration, deduplication
│   ├── serializers.py      # DRF serializers
│   ├── views.py            # Spot API + candidate submission endpoint
│   ├── filters.py          # Bbox, city, tag, query filters for spots
│   ├── nlp_utils.py        # Nigerian food keywords + phone extraction
│   ├── geocoding.py        # Nominatim + 14-city centroid fallback
│   └── dedupe.py           # Name normalization, phone matching, fuzzy dedup
├── verification/           # Human review pipeline
│   ├── models.py           # Verification model (approve/reject/merge)
│   └── views.py            # Queue, action endpoint, dynamic thresholds
├── ingestion/              # Automated discovery intake
│   ├── views.py            # POST /ingest/ and /ingest/batch/ (API key auth)
│   ├── extractors.py       # HTML content extraction utilities
│   └── agents/             # Discovery agents
│       ├── google_maps.py  # Google Places API scanner
│       └── twitter.py      # Twitter/X venue mention extractor
├── whatsapp/               # WhatsApp bot via Twilio
│   ├── models.py           # WhatsAppSession (conversation state)
│   ├── conversation.py     # State machine: awaiting_spot → ... → complete
│   ├── parser.py           # Nigerian spot name/location text parsing
│   └── views.py            # Twilio webhook endpoint
├── users/                  # Custom User with WhatsApp phone + contribution tracking
└── commons/                # BaseModel (created_at, last_modified_at, public_id)
```

## Candidate Lifecycle

```
Submission (raw data)
    ↓  geocode_if_needed()     — Nominatim → city centroid fallback
    ↓  compute_signals()       — keyword hits, has_photo, has_coords
    ↓  compute_score()         — base signals + source channel trust bonus
    ↓  is_duplicate_of_existing() — phone match → dedupe key → fuzzy name+proximity
    ↓
Candidate (pending_verification)
    ↓  verification queue → human approve/reject
    ↓  dynamic threshold: 1 approval (WhatsApp+GPS, Google Maps) or 2 (default)
    ↓
Spot (on the map)
```

## Source-Channel Scoring

Different discovery channels carry different inherent trust levels:

| Channel | Score Bonus | Why |
|---------|-----------|-----|
| Google Maps | +0.35 | Already reviewed by Google's system |
| WhatsApp + GPS | +0.30 | Person is physically at the location |
| WhatsApp (text) | +0.15 | Person knows the spot, no GPS proof |
| Web form + photo | +0.20 | Visual evidence provided |
| Web form | +0.10 | Standard submission |
| Seed script | +0.10 | Extracted from blog content |
| Twitter | +0.05 | Mentions, not confirmations |

Base signals: keyword match (+0.35), has photo (+0.10), has coordinates (+0.10).

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/spots/` | GET | Public | List/filter verified Amala spots (bbox, city, tags, query) |
| `/submit-candidate/` | POST | Public | Manual spot submission from web form |
| `/verify/queue/` | GET | Auth | Candidates pending verification (filterable by city, source_kind, source_channel) |
| `/verify/action/` | POST | Auth | Approve, reject, or merge a candidate |
| `/ingest/` | POST | API Key | Single candidate intake from discovery agents |
| `/ingest/batch/` | POST | API Key | Bulk candidate intake |
| `/whatsapp/webhook/` | POST | Twilio | WhatsApp bot webhook (Twilio signature) |
| `/health/` | GET | Public | Health check |

## Management Commands

```bash
# Bootstrap data from Nigerian food blogs
python manage.py seed_from_blogs [--dry-run] [--urls URL1 URL2]

# Run Google Maps discovery scan for a city
python manage.py run_google_maps_scan --city Lagos

# Run Twitter/X scan for amala spot mentions
python manage.py run_twitter_scan
```

## Getting Started

### Requirements
- Python 3.11+
- PostgreSQL (production) or SQLite (development)

### Installation

```bash
cd amala-atlas-backend-api

# Install dependencies
pipenv install          # or: pip install -r requirements.txt

# Configure environment
cp .env.example .env    # Then edit with your DATABASE_URL, SECRET_KEY, etc.

# Run migrations
python manage.py migrate

# Start the server
python manage.py runserver
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Django secret key |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `DEBUG` | No | `True` for development (default: `False`) |
| `INGEST_API_KEY` | No | API key for `/ingest/` endpoints (default: `dev-ingest-key`) |
| `TWILIO_ACCOUNT_SID` | No | Twilio account SID for WhatsApp bot |
| `TWILIO_AUTH_TOKEN` | No | Twilio auth token |
| `TWILIO_WHATSAPP_NUMBER` | No | Twilio WhatsApp sender number |
| `GOOGLE_MAPS_API_KEY` | No | Google Places API key for discovery agent |
| `TWITTER_BEARER_TOKEN` | No | Twitter API v2 bearer token for discovery agent |

## Testing

```bash
python manage.py test
```

## Deployment

Deployed on [Render](https://amala-atlas.onrender.com) with PostgreSQL.

### CI (Pre-Deploy Validation)

GitHub Actions runs on every pull request and push to `main`/`master`:
- `python manage.py check`
- `python manage.py test`

If CI fails, deployment should be blocked until fixed.

### Render Blueprint (`render.yaml`)

This repository includes a `render.yaml` blueprint configured with:
- **Build Command**: `pip install -r requirements.txt`
- **Pre-Deploy Command**: `python manage.py migrate`
- **Start Command**: `gunicorn amala_atlas.wsgi`
- **Health Check Path**: `/health/`

### Environment Variables

`render.yaml` defines required environment variable keys with `sync: false` so secrets stay in Render and can be synced per environment before deploy:
- `SECRET_KEY`
- `DATABASE_URL`
- `INGEST_API_KEY`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_WHATSAPP_NUMBER`
- `GOOGLE_MAPS_API_KEY`
- `TWITTER_BEARER_TOKEN`

For production, set `DATABASE_URL` from your Aiven PostgreSQL credentials and keep all API keys in Render's secret environment settings.

### Automated Rollback

Enable automatic rollback in your Render service settings so Render reverts a deploy if post-deploy health checks fail.

---

*Part of the [Amala Atlas](https://github.com/AbdulmalikAlayande/Amala-Atlas) ecosystem.*
