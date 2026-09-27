from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed fresh demo users (citizen/authority/ranger/admin), hospitals and dispatch reports."

    def handle(self, *args, **options):
        import seed_demo_data
        seed_demo_data.seed_data()
        self.stdout.write(self.style.SUCCESS("seed_demo_data complete."))
