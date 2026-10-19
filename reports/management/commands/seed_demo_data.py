from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Disabled: Dummy data seeding is permanently disabled to enforce real database records."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING("Notice: Demo data seeding has been permanently disabled per project requirements. The application operates solely on real database records.")
        )
