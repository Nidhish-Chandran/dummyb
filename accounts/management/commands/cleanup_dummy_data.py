from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from reports.models import SightingReport, RangerAssignment
from emergency.models import Hospital
from accounts.models import UserProfile, AccountApplication, Notification, AuditLog


class Command(BaseCommand):
    help = "Safely removes demo, seeded, and test accounts, reports, and hospitals while preserving genuine users and records."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate deletion without committing changes',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        self.stdout.write(self.style.NOTICE(f"Starting data cleanup (dry_run={dry_run})..."))

        # Explicit list of demo/test usernames confirmed for removal
        DEMO_USERNAMES = [
            'authority_demo',
            'ranger_demo',
            'ranger_kollam_2',
            'ranger_kottarakkara',
            'ranger_tvpm',
            'ranger_thrissur',
            'john_citizen',
            'priya_citizen',
            'testcitizentest',
            'testcitizentest2',
            'citizen_e2e_user',
        ]

        # Explicit list of genuine usernames that MUST NEVER be deleted
        GENUINE_USERNAMES = [
            'admin_demo',       # Preserved superuser / admin
            'priya_authority',  # Preserved operational Authority officer
            'Nidhish',          # Genuine citizen (project owner)
            'nehmal12',         # Genuine citizen
        ]

        with transaction.atomic():
            # 1. Reset genuine reports linked to demo assignments
            self.stdout.write("--- 1. Checking genuine reports for demo assignments ---")
            genuine_reports = SightingReport.objects.filter(user__username__in=['Nidhish', 'nehmal12'])
            for gr in genuine_reports:
                # Remove any assignments linking to demo rangers
                demo_assignments = gr.ranger_assignments.filter(ranger__username__in=DEMO_USERNAMES)
                count = demo_assignments.count()
                if count > 0:
                    self.stdout.write(f"Removing {count} demo assignment(s) on genuine Report #{gr.pk} ({gr.title})")
                    if not dry_run:
                        demo_assignments.delete()
                    if gr.assigned_responder and gr.assigned_responder.username in DEMO_USERNAMES:
                        self.stdout.write(f"Unlinking demo responder from Report #{gr.pk}")
                        if not dry_run:
                            gr.assigned_responder = None
                            gr.response_status = SightingReport.RESPONSE_UNASSIGNED
                            gr.save(update_fields=['assigned_responder', 'response_status'])

            # 2. Delete demo assignments on demo reports
            self.stdout.write("--- 2. Removing demo Ranger assignments ---")
            demo_assigns = RangerAssignment.objects.filter(
                ranger__username__in=DEMO_USERNAMES
            ) | RangerAssignment.objects.filter(
                sighting__user__username__in=DEMO_USERNAMES
            )
            assign_count = demo_assigns.count()
            self.stdout.write(f"Found {assign_count} demo assignments to remove.")
            if not dry_run and assign_count > 0:
                demo_assigns.delete()

            # 3. Delete demo sighting reports
            self.stdout.write("--- 3. Removing demo Sighting Reports ---")
            demo_reports = SightingReport.objects.filter(user__username__in=DEMO_USERNAMES)
            # Also catch any unowned seeded reports with sample.jpg
            unowned_seeded = SightingReport.objects.filter(original_image='sightings/sample.jpg')
            all_demo_reports = (demo_reports | unowned_seeded).distinct()
            report_count = all_demo_reports.count()
            self.stdout.write(f"Found {report_count} demo reports to remove.")
            if not dry_run and report_count > 0:
                all_demo_reports.delete()

            # 4. Delete demo/test hospitals
            self.stdout.write("--- 4. Removing demo/fabricated hospital records ---")
            hospitals = Hospital.objects.all()
            hosp_count = hospitals.count()
            self.stdout.write(f"Found {hosp_count} hospital records to remove.")
            if not dry_run and hosp_count > 0:
                hospitals.delete()

            # 5. Clean up notifications & audit logs referencing demo users
            self.stdout.write("--- 5. Removing notifications & audit entries for demo users ---")
            demo_notifs = Notification.objects.filter(recipient__username__in=DEMO_USERNAMES)
            notif_count = demo_notifs.count()
            if not dry_run and notif_count > 0:
                demo_notifs.delete()
            self.stdout.write(f"Removed {notif_count} demo notifications.")

            demo_audits = AuditLog.objects.filter(actor__username__in=DEMO_USERNAMES)
            audit_count = demo_audits.count()
            if not dry_run and audit_count > 0:
                demo_audits.delete()
            self.stdout.write(f"Removed {audit_count} demo audit entries.")

            # 6. Delete demo & test user accounts
            self.stdout.write("--- 6. Removing demo & test user accounts ---")
            users_to_delete = User.objects.filter(username__in=DEMO_USERNAMES)
            user_count = users_to_delete.count()
            for u in users_to_delete:
                self.stdout.write(f"  - Deleting demo user: {u.username} (role: {getattr(u, 'profile', None)})")
            if not dry_run and user_count > 0:
                users_to_delete.delete()

            # 7. Verification of preserved records
            self.stdout.write("--- 7. Verification of preserved records ---")
            preserved_users = list(User.objects.values_list('username', flat=True))
            self.stdout.write(f"Preserved active users ({len(preserved_users)}): {preserved_users}")
            preserved_reports = list(SightingReport.objects.values('id', 'title', 'user__username', 'status'))
            self.stdout.write(f"Preserved genuine reports ({len(preserved_reports)}):")
            for pr in preserved_reports:
                self.stdout.write(f"  - Report #{pr['id']}: '{pr['title']}' by {pr['user__username']} [{pr['status']}]")

            if dry_run:
                self.stdout.write(self.style.WARNING("Dry run completed: no database modifications were committed."))
                transaction.set_rollback(True)
            else:
                self.stdout.write(self.style.SUCCESS("Cleanup committed successfully."))
