import os
import django
import sys

# Add the backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "amala-atlas-backend-api"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "amala_atlas.settings")
django.setup()

from rest_framework.test import APIClient
from places.models import Submission, Candidate, PhotoURL

def test_multi_photo_submission():
    client = APIClient()
    url = '/submit-candidate/'
    data = {
        "name": "Test Multi Photo Buka",
        "address": "123 Test Street",
        "city": "Lagos",
        "country": "Nigeria",
        "lat": 6.5244,
        "lng": 3.3792,
        "photo_urls": [
            "https://example.com/photo1.jpg",
            "https://example.com/photo2.jpg"
        ]
    }
    
    response = client.post(url, data, format='json')
    
    if response.status_code == 201:
        print("Submission successful!")
        submission = Submission.objects.filter(name="Test Multi Photo Buka").latest('created_at')
        photos = PhotoURL.objects.filter(content_type__model='submission', object_id=submission.id)
        print(f"Submission photos found: {photos.count()}")
        for p in photos:
            print(f" - {p.url}")
            
        candidate = Candidate.objects.filter(name="Test Multi Photo Buka").latest('created_at')
        c_photos = PhotoURL.objects.filter(content_type__model='candidate', object_id=candidate.id)
        print(f"Candidate photos found: {c_photos.count()}")
        for p in c_photos:
            print(f" - {p.url}")
            
        if photos.count() == 2 and c_photos.count() == 2:
            print("Multi-photo test PASSED")
        else:
            print("Multi-photo test FAILED: Unexpected number of photos")
    else:
        print(f"Submission failed with status {response.status_code}")
        print(response.data)

if __name__ == "__main__":
    test_multi_photo_submission()
