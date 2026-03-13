"""
Run the Google Maps Places API agent for a specific city.

Usage:
    python manage.py run_google_maps_scan --city Lagos
    python manage.py run_google_maps_scan --city Ibadan
    python manage.py run_google_maps_scan --all
"""

from django.core.management.base import BaseCommand

from ingestion.agents.google_maps import scan_google_maps
from places.geocoding import CITY_CENTROIDS


class Command(BaseCommand):
    help = "Scan Google Maps for Amala spots in Nigerian cities"

    def add_arguments(self, parser):
        parser.add_argument('--city', type=str, help='City to scan (e.g. Lagos, Ibadan)')
        parser.add_argument('--all', action='store_true', help='Scan all known cities')

    def handle(self, *args, **options):
        if options['all']:
            cities = [c.title() for c in CITY_CENTROIDS.keys()]
        elif options['city']:
            cities = [options['city']]
        else:
            cities = ['Lagos', 'Ibadan']

        for city in cities:
            self.stdout.write(f"\nScanning Google Maps for: {city}")
            result = scan_google_maps(city)
            self.stdout.write(self.style.SUCCESS(
                f"  Results: {result['created']} created, {result['duplicates']} duplicates, "
                f"{result['errors']} errors (total: {result['total']})"
            ))

        self.stdout.write(self.style.SUCCESS("\nDone."))
