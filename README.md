# Amala Atlas — Backend API

[![Django](https://img.shields.io/badge/Django-5.0+-092e20.svg)](https://www.djangoproject.com)
[![DRF](https://img.shields.io/badge/DRF-3.14+-red.svg)](https://www.django-rest-framework.org)

The **Amala Atlas Backend** is the system of record for the Amala Atlas ecosystem. It provides the RESTful API for candidate ingestion, verification workflows, and serves the canonical database of verified Amala spots.

---

## 🏗️ Architecture

The backend manages the lifecycle of a "Spot":
1.  **Ingestion:** Discovered candidates are POSTed from the Auto-Discovery service.
2.  **Verification:** Candidates enter a verification queue where they are reviewed and promoted to "Spots".
3.  **Consumption:** Verified Spots are served via public APIs for the frontend.

### Core Apps:
- `places`: Manages `Spot` and `Candidate` models.
- `verification`: Logic for human-in-the-loop review and promotion.
- `ingestion`: API endpoints for machine-driven discovery intake.
- `users`: Custom user management.

---

## 🛠️ Tech Stack
- **Framework:** Django 5.x
- **API:** Django REST Framework (DRF)
- **Database:** PostgreSQL (Production), SQLite (Dev)
- **Environment:** `Pipenv` or `requirements.txt`

---

## 🚦 Getting Started

### Requirements
- Python 3.11+
- SQLite or PostgreSQL

### Installation
1.  Navigate to the backend directory:
    ```bash
    cd amala-atlas-backend-api
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run migrations:
    ```bash
    python manage.py migrate
    ```
4.  Load seed data (optional):
    ```bash
    python manage.py loaddata fixtures/seeds_core.json
    ```

### Configuration
Create a `.env` file in `amala-atlas-backend-api/`:
```env
DEBUG=True
SECRET_KEY=your_secret_key
DATABASE_URL=sqlite:///db.sqlite3
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/spots/` | GET | List all verified Amala spots |
| `/ingest/` | POST | Intake for Auto-Discovery candidates |
| `/verify/queue/` | GET | List candidates awaiting verification |
| `/verify/action/` | POST | Approve, reject, or merge candidates |
| `/submit-candidate/` | POST | Public endpoint for manual submissions |
| `/health/` | GET | System health check |

---

## 🧪 Testing & Engineering
- **Unit Tests:** `python manage.py test`
- **Engineering Practices:**
  - **Unit & Integration Testing:** Comprehensive coverage for verification logic and API serializers.
  - **Code Reviews:** Strict adherence to Django best practices.
  - **CI/CD:** Automated testing on push.

---

## 📝 TODOs
- [ ] Implement Geohash-based proximity search.
- [ ] Add support for multi-photo uploads.
- [ ] Implement rate-limiting for public submission endpoints.