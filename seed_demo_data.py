import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'venomwatch.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile
from reports.models import SightingReport
from emergency.models import Hospital
from ai.services import SNAKE_SPECIES_DATABASE as SNAKE_DATABASE

def seed_data():
    print("Seeding Venom Watch Demo Data...")

    # 1. Create Superuser / Admin & Authority Officers
    admin_user, created = User.objects.get_or_create(username='admin', defaults={
        'email': 'admin@venomwatch.org',
        'is_staff': True,
        'is_superuser': True
    })
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("Created Superuser: admin / admin123")

    ranger_user, created = User.objects.get_or_create(username='ranger_officer', defaults={
        'email': 'ranger@forest.gov.in',
        'is_staff': True
    })
    if created:
        ranger_user.set_password('ranger123')
        ranger_user.save()
        ranger_user.profile.role = UserProfile.ROLE_RANGER
        ranger_user.profile.organization = 'State Forest Department - Wildlife Division'
        ranger_user.profile.save()
        print("Created Authority User: ranger_officer / ranger123")

    citizen_user, created = User.objects.get_or_create(username='john_citizen', defaults={
        'email': 'john@gmail.com'
    })
    if created:
        citizen_user.set_password('citizen123')
        citizen_user.save()
        print("Created Citizen User: john_citizen / citizen123")

    # 2. Seed Emergency Hospitals
    hospitals_data = [
        {
            'name': 'Government Medical College Hospital & Trauma Center',
            'phone_number': '108 / +91 484 2555555',
            'address': 'Kalamassery Main Road, Sector 1',
            'latitude': 10.0456,
            'longitude': 76.3212,
            'anti_venom_available': True,
            'anti_venom_stock_vials': 85,
            'has_icu': True,
            'operating_hours': '24/7 Trauma Emergency Care'
        },
        {
            'name': 'District Anti-Venom Specialty Emergency Clinic',
            'phone_number': '+91 484 2360001',
            'address': 'MG Road Bypass, Near General Hospital',
            'latitude': 9.9723,
            'longitude': 76.2801,
            'anti_venom_available': True,
            'anti_venom_stock_vials': 40,
            'has_icu': True,
            'operating_hours': '24/7 Emergency Care'
        },
        {
            'name': 'Lakeside Wildlife & Toxicology Hospital',
            'phone_number': '+91 484 2701100',
            'address': 'NH 66 Bypass, Nettoor Junction',
            'latitude': 9.9211,
            'longitude': 76.3054,
            'anti_venom_available': True,
            'anti_venom_stock_vials': 60,
            'has_icu': True,
            'operating_hours': '24/7 Emergency Care'
        }
    ]

    for h in hospitals_data:
        Hospital.objects.get_or_create(name=h['name'], defaults=h)

    print("Hospitals populated.")

    # 3. Seed Sample Sighting Reports (Clustered for DBSCAN Hotspots)
    if SightingReport.objects.count() == 0:
        sample_reports = [
            # High Alert Cluster 1 (Kochi Central)
            {
                'title': 'Spectacled Cobra Hooded Near Garden Gate',
                'latitude': 9.9312,
                'longitude': 76.2673,
                'location_name': 'Kochi Sector 4 Residential Belt',
                'species_predicted': 'Indian Cobra (Naja naja)',
                'common_name': 'Spectacled Cobra',
                'venom_category': 'HIGHLY_VENOMOUS',
                'toxicity_level': 'CRITICAL',
                'danger_score': 95,
                'ai_confidence': 96.8,
                'notes': 'Large hooded cobra observed near drainage pipe.',
                'status': 'VERIFIED'
            },
            {
                'title': 'Second Cobra Sighting Near Sector 4 Park',
                'latitude': 9.9330,
                'longitude': 76.2690,
                'location_name': 'Kochi Sector 4 Residential Belt',
                'species_predicted': 'Indian Cobra (Naja naja)',
                'common_name': 'Spectacled Cobra',
                'venom_category': 'HIGHLY_VENOMOUS',
                'toxicity_level': 'CRITICAL',
                'danger_score': 95,
                'ai_confidence': 94.2,
                'notes': 'Moving towards coconut grove.',
                'status': 'VERIFIED'
            },
            {
                'title': "Russell's Viper Coiled Near Construction Site",
                'latitude': 9.9305,
                'longitude': 76.2650,
                'location_name': 'Kochi Sector 4 Residential Belt',
                'species_predicted': "Russell's Viper (Daboia russelii)",
                'common_name': 'Chitraj',
                'venom_category': 'HIGHLY_VENOMOUS',
                'toxicity_level': 'CRITICAL',
                'danger_score': 98,
                'ai_confidence': 97.5,
                'notes': 'Loud hissing heard. Heavy body pattern.',
                'status': 'PENDING'
            },
            # Green Safe Spot 1 (Aluva Sector)
            {
                'title': 'Harmless Rat Snake Clearing Rodents',
                'latitude': 10.1004,
                'longitude': 76.3570,
                'location_name': 'Aluva River Bank',
                'species_predicted': 'Indian Rat Snake (Ptyas mucosa)',
                'common_name': 'Dhaman',
                'venom_category': 'NON_VENOMOUS',
                'toxicity_level': 'SAFE',
                'danger_score': 10,
                'ai_confidence': 98.1,
                'notes': 'Slender brown snake running fast through grass.',
                'status': 'VERIFIED'
            },
            # High Alert Cluster 2 (Kalamassery Industrial Zone)
            {
                'title': 'Common Krait Hiding Under Brick Pile',
                'latitude': 10.0420,
                'longitude': 76.3200,
                'location_name': 'Kalamassery Industrial Area',
                'species_predicted': 'Common Krait (Bungarus caeruleus)',
                'common_name': 'Krait',
                'venom_category': 'HIGHLY_VENOMOUS',
                'toxicity_level': 'CRITICAL',
                'danger_score': 99,
                'ai_confidence': 95.9,
                'notes': 'Narrow white crossbars visible.',
                'status': 'PENDING'
            },
            {
                'title': 'Green Pit Viper in Mango Tree Branch',
                'latitude': 10.0440,
                'longitude': 76.3220,
                'location_name': 'Kalamassery Industrial Area',
                'species_predicted': 'Bamboo Pit Viper (Trimeresurus gramineus)',
                'common_name': 'Green Pit Viper',
                'venom_category': 'VENOMOUS',
                'toxicity_level': 'MODERATE_HIGH',
                'danger_score': 75,
                'ai_confidence': 93.4,
                'notes': 'Bright green body, triangular head.',
                'status': 'VERIFIED'
            }
        ]

        for s in sample_reports:
            # Create a simple placeholder image for seeded records
            SightingReport.objects.create(
                user=citizen_user,
                original_image='sightings/sample.jpg',
                processed_image='processed_sightings/sample_ai.jpg',
                **s
            )

        print("Sample sightings seeded successfully.")

    print("Demo Data Seeding Finished Successfully!")

if __name__ == '__main__':
    seed_data()
