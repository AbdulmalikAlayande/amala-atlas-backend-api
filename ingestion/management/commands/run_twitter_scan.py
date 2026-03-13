"""
Run the Twitter/X monitoring agent.

Usage:
    python manage.py run_twitter_scan
"""

from django.core.management.base import BaseCommand

from ingestion.agents.twitter import scan_twitter


class Command(BaseCommand):
    help = "Scan Twitter/X for Amala spot mentions"

    def handle(self, *args, **options):
        self.stdout.write("Scanning Twitter for Amala spot mentions...")
        result = scan_twitter()

        if result.get('error'):
            self.stderr.write(self.style.ERROR(f"Error: {result['error']}"))
            return

        self.stdout.write(self.style.SUCCESS(
            f"Results: {result['created']} created, {result['duplicates']} duplicates, "
            f"{result['skipped']} skipped, {result['errors']} errors (total: {result['total']})"
        ))
