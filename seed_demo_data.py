import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'venomwatch.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile
from reports.models import SightingReport
from emergency.models import Hospital
SNAKE_DATABASE = {}

def seed_data():
    print("Seeding Venom Watch Demo Data...")

    # 1. Create Superuser / Admin & Authority Officers
    admin_user, created = User.objects.get_or_create(username='admin_demo', defaults={
        'email': 'admin@venomwatch.org',
        'is_staff': True,
        'is_superuser': True
    })
    if created:
        admin_user.set_password('admin_demo123')
        admin_user.save()
        print("Created Superuser: admin_demo / admin_demo123")

    authority_user, created = User.objects.get_or_create(username='authority_demo', defaults={
        'email': 'officer@forest.gov.in',
        'is_staff': False,
        'is_superuser': False
    })
    if created:
        authority_user.set_password('authority_demo123')
        authority_user.save()
        authority_user.profile.role = UserProfile.ROLE_AUTHORITY
        authority_user.profile.organization = 'State Forest Department - Wildlife Division'
        authority_user.profile.save()
        print("Created Authority console user: authority_demo / authority_demo123")

    # Ensure the superuser's profile carries the ADMIN role even if it pre-existed
    admin_profile = admin_user.profile
    if admin_profile.role != UserProfile.ROLE_ADMIN:
        admin_profile.role = UserProfile.ROLE_ADMIN
        admin_profile.full_name = 'Platform Administrator'
        admin_profile.save()

    # Ensure the superuser's profile carries the ADMIN role even if it pre-existed
    admin_profile = admin_user.profile
    if admin_profile.role != UserProfile.ROLE_ADMIN:
        admin_profile.role = UserProfile.ROLE_ADMIN
        admin_profile.full_name = 'Platform Administrator'
        admin_profile.save()

    # 1b. Demo Rangers — different registered operational bases (for location-based dispatch)
    RANGER_PASSWORD = 'ranger_demo123'
    rangers_data = [
        {'username': 'ranger_demo',       'first_name': 'Arun Kumar',    'last_name': '', 'registered_location': 'Kollam',             'latitude': 8.8932,  'longitude': 76.6141},
        {'username': 'ranger_kollam_2',   'first_name': 'Meera Nair',    'last_name': '', 'registered_location': 'Kollam',             'latitude': 8.8805,  'longitude': 76.5980},
        {'username': 'ranger_kottarakkara','first_name': 'Suresh Menon', 'last_name': '', 'registered_location': 'Kottarakkara',       'latitude': 8.8853,  'longitude': 76.7904},
        {'username': 'ranger_tvpm',       'first_name': 'Fathima Beevi', 'last_name': '', 'registered_location': 'Thiruvananthapuram', 'latitude': 8.5241,  'longitude': 76.9366},
    ]
    for rd in rangers_data:
        uname = rd.pop('username')
        r, made = User.objects.get_or_create(username=uname, defaults={'email': f'{uname}@forest.gov.in'})
        if made:
            r.set_password(RANGER_PASSWORD)
            r.first_name = rd['first_name']
            r.last_name = rd['last_name']
            r.save()
        prof = r.profile
        prof.role = UserProfile.ROLE_RANGER
        prof.organization = 'State Forest Department - Snake Rescue Unit'
        prof.registered_location = rd['registered_location']
        prof.latitude = rd['latitude']
        prof.longitude = rd['longitude']
        prof.availability = UserProfile.AVAILABILITY_AVAILABLE
        prof.save()
    print("Demo rangers seeded: ranger_demo, ranger_kollam_2 (Kollam), ranger_kottarakkara, ranger_tvpm — password: " + RANGER_PASSWORD)

    citizens_data = [
        {'username': 'john_citizen', 'email': 'john@gmail.com',   'first_name': 'John',  'last_name': 'Mathew'},
        {'username': 'priya_citizen','email': 'priya@gmail.com',  'first_name': 'Priya', 'last_name': 'Nair'},
    ]
    for cd in citizens_data:
        c, made = User.objects.get_or_create(username=cd['username'], defaults={'email': cd['email']})
        if made:
            c.set_password('citizen_demo123')
            c.first_name = cd['first_name']
            c.last_name = cd['last_name']
            c.save()
            c.profile.role = UserProfile.ROLE_CITIZEN
            c.profile.full_name = f"{cd['first_name']} {cd['last_name']}"
            c.profile.save()
    print("Citizen users seeded: john_citizen, priya_citizen — password: citizen_demo123")

    # Keep a reference used by the sample-report seeder below
    citizen_user = User.objects.get(username='john_citizen')

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

    # 3b. Location-dispatch demo reports (Kollam vs Thrissur) so the
    #     Authority "Assign Ranger" list changes with report location.
    dispatch_reports = [
        {
            'title': 'Cobra near paddy field by Kallada bridge',
            'latitude': 8.9200, 'longitude': 76.6000,
            'location_name': 'Kollam town, Asramam ground',
            'species_predicted': 'Indian Cobra (Naja naja)',
            'common_name': 'Spectacled Cobra',
            'venom_category': 'HIGHLY_VENOMOUS', 'toxicity_level': 'CRITICAL',
            'danger_score': 92, 'ai_confidence': 91.5,
            'notes': 'Demo incident for ranger dispatch testing.',
        },
        {
            'title': 'Viper spotted behind Thrissur round bus stand',
            'latitude': 10.5276, 'longitude': 76.2144,
            'location_name': 'Thrissur Swaraj Round',
            'species_predicted': "Russell's Viper (Daboia russelii)",
            'common_name': 'Chitraj',
            'venom_category': 'HIGHLY_VENOMOUS', 'toxicity_level': 'CRITICAL',
            'danger_score': 96, 'ai_confidence': 89.0,
            'notes': 'Demo far-away incident — should show different rangers.',
        },
    ]
    dispatcher = User.objects.filter(username='john_citizen').first()
    for dr in dispatch_reports:
        exists = SightingReport.objects.filter(title=dr['title']).exists()
        if not exists and dispatcher:
            SightingReport.objects.create(user=dispatcher, **dr)
    print("Dispatch demo reports seeded (Kollam + Thrissur).")

    print("Demo Data Seeding Finished Successfully!")

if __name__ == '__main__':
    seed_data()
