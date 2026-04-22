import json
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db.models import Q
from places.models import Spot

class Command(BaseCommand):
    help = 'Clean and enrich spot data by filling in missing fields'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes'
        )
        parser.add_argument(
            '--city',
            type=str,
            help='Enrich spots for a specific city'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        city_filter = options.get('city')

        self.stdout.write(self.style.SUCCESS('Starting data enrichment...'))

        # Find spots with missing critical fields
        queryset = Spot.objects.all()
        if city_filter:
            queryset = queryset.filter(city__iexact=city_filter)

        # Identify problematic spots
        empty_city = queryset.filter(Q(city__isnull=True) | Q(city__exact=''))
        empty_state = queryset.filter(Q(state__isnull=True) | Q(state__exact=''))
        empty_address = queryset.filter(Q(address__isnull=True) | Q(address__exact=''))
        empty_phone = queryset.filter(Q(phone__isnull=True) | Q(phone__exact=''))
        invalid_coords = queryset.filter(Q(lat__isnull=True) | Q(lng__isnull=True))
        empty_name = queryset.filter(Q(name__isnull=True) | Q(name__exact=''))

        self.stdout.write(f'\n[DATA QUALITY REPORT]')
        self.stdout.write(f'  Spots with missing city: {empty_city.count()}')
        self.stdout.write(f'  Spots with missing state: {empty_state.count()}')
        self.stdout.write(f'  Spots with missing address: {empty_address.count()}')
        self.stdout.write(f'  Spots with missing phone: {empty_phone.count()}')
        self.stdout.write(f'  Spots with invalid coordinates: {invalid_coords.count()}')
        self.stdout.write(f'  Spots with missing name: {empty_name.count()}')

        # Load state-cities data
        state_cities = self._load_state_cities_data()

        # Enrich spots
        updated_count = 0

        for spot in queryset:
            updates = {}

            # Fill in missing city/state from lat/lng if possible
            if not spot.city or spot.city == '':
                city = self._get_city_from_latlng(spot.lat, spot.lng, state_cities)
                if city:
                    updates['city'] = city
                    self.stdout.write(f'  → {spot.name}: city = {city}')

            if not spot.state or spot.state == '':
                state = self._get_state_from_latlng(spot.lat, spot.lng, state_cities)
                if state:
                    updates['state'] = state
                    self.stdout.write(f'  → {spot.name}: state = {state}')

            # Normalize phone numbers
            if spot.phone and spot.phone.strip():
                normalized = self._normalize_phone(spot.phone)
                if normalized != spot.phone:
                    updates['phone'] = normalized

            # Ensure country is set
            if not spot.country or spot.country == '':
                updates['country'] = 'Nigeria'

            # Update the spot if there are changes
            if updates:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'[DRY RUN] Would update {spot.name}: {updates}'
                        )
                    )
                else:
                    for field, value in updates.items():
                        setattr(spot, field, value)
                    spot.save(update_fields=list(updates.keys()))
                    updated_count += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\n[DRY RUN] Would update {updated_count} spots')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Updated {updated_count} spots')
            )

        self.stdout.write(self.style.SUCCESS('Enrichment complete!'))

    def _load_state_cities_data(self):
        """Load state-cities data from JSON files."""
        data_dir = Path(__file__).parent.parent.parent.parent / 'amala-atlas-explorer' / 'data' / 'state-cities-lat-long-dataset'
        state_cities = {}

        if data_dir.exists():
            for json_file in data_dir.glob('*.json'):
                state_name = json_file.stem.title()
                try:
                    with open(json_file) as f:
                        cities_data = json.load(f)
                        cities = [c['name'] for c in cities_data]
                        state_cities[state_name] = {
                            'cities': list(set(cities)),
                            'raw_data': cities_data
                        }
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error loading {json_file}: {e}'))

        return state_cities

    def _get_city_from_latlng(self, lat, lng, state_cities):
        """Find closest city based on lat/lng."""
        if not state_cities:
            return None

        min_distance = float('inf')
        closest_city = None

        for state, data in state_cities.items():
            for city_data in data['raw_data']:
                distance = self._haversine_distance(
                    lat, lng, city_data['lat'], city_data['long']
                )
                if distance < min_distance and distance < 5:  # 5km threshold
                    min_distance = distance
                    closest_city = city_data['name']

        return closest_city

    def _get_state_from_latlng(self, lat, lng, state_cities):
        """Find state based on lat/lng."""
        if not state_cities:
            return None

        min_distance = float('inf')
        closest_state = None

        for state, data in state_cities.items():
            for city_data in data['raw_data']:
                distance = self._haversine_distance(
                    lat, lng, city_data['lat'], city_data['long']
                )
                if distance < min_distance and distance < 5:
                    min_distance = distance
                    closest_state = state

        return closest_state

    def _haversine_distance(self, lat1, lng1, lat2, lng2):
        """Calculate distance between two points in km."""
        from math import radians, cos, sin, asin, sqrt

        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlng = lng2 - lng1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return km

    def _normalize_phone(self, phone):
        """Normalize phone number."""
        # Remove extra whitespace
        normalized = phone.strip()
        # Add country code if missing
        if normalized and not normalized.startswith('+'):
            if normalized.startswith('0'):
                normalized = '+234' + normalized[1:]
            elif normalized.startswith('234'):
                normalized = '+' + normalized
        return normalized
