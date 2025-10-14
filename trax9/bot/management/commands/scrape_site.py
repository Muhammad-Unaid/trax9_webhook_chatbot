from django.core.management.base import BaseCommand
from bot.web_scrap import scrape_and_sync

class Command(BaseCommand):
    help = "Auto scrape and sync site content"

    def handle(self, *args, **kwargs):
        domain = "https://trax9.com/"
        results = scrape_and_sync(domain)
        created = len([r for r in results if r[1] == "created"])
        updated = len([r for r in results if r[1] == "updated"])
        skipped = len([r for r in results if r[1] == "skipped"])
        failed = len([r for r in results if r[1] in ("failed","error")])
        self.stdout.write(self.style.SUCCESS(
            f"Scrape finished. Created: {created}, Updated: {updated}, Skipped: {skipped}, Failed: {failed}"
        ))
        for url, action in results:
            self.stdout.write(f"{action.upper():7}  {url}")
