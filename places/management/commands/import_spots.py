# places/management/commands/import_spots.py
import json
from django.core.management.base import BaseCommand
from places.models import Spot


class Command(BaseCommand):
    help = 'Import spots from JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to JSON file')

    def handle(self, *args, **options):
        json_file = options['json_file']

        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        spots_to_create = []

        for item in data:
            fields = item['fields']
            # Remove pk if you want auto-generated IDs, or keep it
            spot = Spot(
                # id=item['pk'],  # Uncomment if you want to preserve PKs
                name=fields['name'],
                lat=fields['lat'],
                lng=fields['lng'],
                address=fields['address'],
                city=fields['city'],
                state=fields['state'],
                country=fields['country'],
                zipcode=fields['zipcode'],
                price_band=fields['price_band'],
                tags=fields['tags'],
                hours_text=fields['hours_text'],
                phone=fields['phone'],
                website=fields['website'],
                email=fields['email'],
                amala_focus=fields['amala_focus'],
                photos=fields['photos'],
                open_hours=fields['open_hours'],
                source=fields['source']
            )
            spots_to_create.append(spot)

        # Bulk create all at once (much faster)
        Spot.objects.bulk_create(spots_to_create, ignore_conflicts=True)

        self.stdout.write(
            self.style.SUCCESS(f'Successfully imported {len(spots_to_create)} spots')
        )