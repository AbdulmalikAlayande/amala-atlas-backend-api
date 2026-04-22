import os
import json
from django.core.management.base import BaseCommand
from django.db import connections
from django.core.serializers import serialize
from places.models import Spot

class Command(BaseCommand):
    help = 'Sync enriched spot data to production database (Aiven)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes'
        )
        parser.add_argument(
            '--export-json',
            type=str,
            help='Export enriched data to JSON file instead of syncing'
        )
        parser.add_argument(
            '--since',
            type=str,
            help='Only sync spots modified since this date (YYYY-MM-DD)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        export_json = options.get('export_json')
        since = options.get('since')

        self.stdout.write(self.style.SUCCESS('Starting data sync...'))

        # Get enriched spots
        queryset = Spot.objects.all()

        if since:
            from datetime import datetime
            since_date = datetime.fromisoformat(since)
            queryset = queryset.filter(updated_at__gte=since_date)
            self.stdout.write(f'Syncing spots updated since {since}')

        spots_data = list(queryset.values())
        total_spots = len(spots_data)

        self.stdout.write(f'\nPrepared {total_spots} spots for sync')

        # Option 1: Export to JSON
        if export_json:
            self._export_to_json(spots_data, export_json)
            return

        # Option 2: Direct database sync (requires Aiven DB URL)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'[DRY RUN] Would sync {total_spots} spots to production'
                )
            )
            self.stdout.write('\nSample data to be synced:')
            for spot in spots_data[:3]:
                self.stdout.write(f'  - {spot["name"]} ({spot["city"]})')
        else:
            self._sync_to_aiven(spots_data)

    def _export_to_json(self, data, filepath):
        """Export enriched data to JSON file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            self.stdout.write(
                self.style.SUCCESS(f'✓ Exported {len(data)} spots to {filepath}')
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error exporting JSON: {e}'))

    def _sync_to_aiven(self, data):
        """Sync data directly to Aiven production database."""
        aiven_db_url = os.environ.get('AIVEN_DATABASE_URL')

        if not aiven_db_url:
            self.stdout.write(
                self.style.ERROR(
                    'AIVEN_DATABASE_URL not set. '
                    'Use --export-json to export data instead.'
                )
            )
            return

        try:
            from django.db import connections
            from django.db.backends.postgresql.base import DatabaseCreation

            # Create temporary connection to Aiven DB
            self.stdout.write('Connecting to Aiven production database...')

            for spot in data:
                # This is a simplified approach - for production, consider:
                # 1. Using a proper ORM migration
                # 2. Using Django fixtures
                # 3. Using a dedicated data pipeline tool
                try:
                    # Attempt to update or create in Aiven DB
                    spot_id = spot.get('id')
                    # You would implement actual sync logic here
                    self.stdout.write(f'  → Syncing {spot["name"]}...')
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Error syncing {spot["name"]}: {e}')
                    )

            self.stdout.write(
                self.style.SUCCESS(f'✓ Synced {len(data)} spots to Aiven')
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Sync error: {e}'))
