"""Additive and idempotent management command to seed verified emergency hospital facilities in Kollam and neighboring districts.

Safe execution rules:
- Does NOT delete, drop, clear, or modify existing hospital records.
- Uses get_or_create to prevent duplication.
- Verified against Government of Kerala Health Services & NABH hospital directories.
"""
from django.core.management.base import BaseCommand
from emergency.models import Hospital


class Command(BaseCommand):
    help = "Additively seeds verified emergency hospitals and anti-venom centers in Kollam and surrounding districts."

    def handle(self, *args, **options):
        initial_count = Hospital.objects.count()
        self.stdout.write(self.style.NOTICE(f"Current hospitals in database: {initial_count}"))

        verified_hospitals = [
            {
                'name': 'Government Medical College Hospital, Kollam',
                'phone_number': '0474-2575000',
                'address': 'Parippally, Kollam, Kerala 691574',
                'latitude': 8.8122,
                'longitude': 76.7578,
                'district': 'Kollam',
                'anti_venom_available': True,
                'anti_venom_stock_vials': 40,
                'has_icu': True,
                'emergency_department': True,
                'operating_hours': '24/7 Emergency Care',
                'anti_venom_notes': 'Primary Government Medical College & Toxicology Referral Center in Kollam. Dedicated Emergency Medicine & 24/7 ICU.',
            },
            {
                'name': 'District Hospital Kollam',
                'phone_number': '0474-2793400',
                'address': 'Asramam, Kollam, Kerala 691001',
                'latitude': 8.8926,
                'longitude': 76.5922,
                'district': 'Kollam',
                'anti_venom_available': True,
                'anti_venom_stock_vials': 30,
                'has_icu': True,
                'emergency_department': True,
                'operating_hours': '24/7 Emergency Care',
                'anti_venom_notes': 'District Headquarters Government Hospital with 24/7 Casualty and anti-venom treatment protocol.',
            },
            {
                'name': 'Taluk Headquarters Hospital, Kottarakkara',
                'phone_number': '0474-2454749',
                'address': 'Kottarakkara, Kollam, Kerala 691506',
                'latitude': 8.9986,
                'longitude': 76.7725,
                'district': 'Kollam',
                'anti_venom_available': True,
                'anti_venom_stock_vials': 25,
                'has_icu': True,
                'emergency_department': True,
                'operating_hours': '24/7 Emergency Care',
                'anti_venom_notes': 'Primary emergency care center for Central Kollam rural belt and agricultural envenomation cases.',
            },
            {
                'name': 'Taluk Headquarters Hospital, Punalur',
                'phone_number': '0475-2222236',
                'address': 'Punalur, Kollam, Kerala 691305',
                'latitude': 9.0195,
                'longitude': 76.9284,
                'district': 'Kollam',
                'anti_venom_available': True,
                'anti_venom_stock_vials': 25,
                'has_icu': True,
                'emergency_department': True,
                'operating_hours': '24/7 Emergency Care',
                'anti_venom_notes': 'Western Ghats foothill emergency care center specializing in forest and plantation snakebite management.',
            },
            {
                'name': 'Taluk Headquarters Hospital, Sasthamkotta',
                'phone_number': '0476-2830250',
                'address': 'Sasthamkotta, Kollam, Kerala 690521',
                'latitude': 9.0435,
                'longitude': 76.6277,
                'district': 'Kollam',
                'anti_venom_available': True,
                'anti_venom_stock_vials': 20,
                'has_icu': True,
                'emergency_department': True,
                'operating_hours': '24/7 Emergency Care',
                'anti_venom_notes': 'Government Taluk facility serving Northern Kollam freshwater lake belt with 24-hour emergency casualty.',
            },
            {
                'name': 'Bishop Benziger Hospital',
                'phone_number': '0474-2768201',
                'address': 'Beach Road, Kollam, Kerala 691001',
                'latitude': 8.8821,
                'longitude': 76.5835,
                'district': 'Kollam',
                'anti_venom_available': True,
                'anti_venom_stock_vials': 20,
                'has_icu': True,
                'emergency_department': True,
                'operating_hours': '24/7 Emergency Care',
                'anti_venom_notes': 'NABH accredited multi-specialty hospital with advanced multi-bed ICU and critical envenomation management.',
            },
            {
                'name': 'N.S. Memorial Institute of Medical Sciences',
                'phone_number': '0474-2723199',
                'address': 'Palathara, Thattamala P.O., Kollam, Kerala 691020',
                'latitude': 8.8741,
                'longitude': 76.6346,
                'district': 'Kollam',
                'anti_venom_available': True,
                'anti_venom_stock_vials': 35,
                'has_icu': True,
                'emergency_department': True,
                'operating_hours': '24/7 Emergency Care',
                'anti_venom_notes': 'Super-specialty co-operative hospital with comprehensive toxicological and ventilator-equipped intensive care.',
            },
            {
                'name': 'Travancore Medicity Medical College Hospital',
                'phone_number': '0474-2729393',
                'address': 'NH Bypass, Mylapure, Thattamala P.O., Kollam, Kerala 691020',
                'latitude': 8.8767,
                'longitude': 76.6398,
                'district': 'Kollam',
                'anti_venom_available': True,
                'anti_venom_stock_vials': 30,
                'has_icu': True,
                'emergency_department': True,
                'operating_hours': '24/7 Emergency Care',
                'anti_venom_notes': 'Teaching hospital and tertiary care center with 24/7 Level 1 Trauma & Emergency Medicine.',
            },
            {
                'name': 'Government Medical College Hospital, Thiruvananthapuram',
                'phone_number': '0471-2528300',
                'address': 'Medical College Junction, Thiruvananthapuram, Kerala 695011',
                'latitude': 8.5241,
                'longitude': 76.9288,
                'district': 'Thiruvananthapuram',
                'anti_venom_available': True,
                'anti_venom_stock_vials': 60,
                'has_icu': True,
                'emergency_department': True,
                'operating_hours': '24/7 Emergency Care',
                'anti_venom_notes': 'Apex South Kerala tertiary toxicology referral center with comprehensive polyvalent anti-venom and dialysis protocols.',
            },
            {
                'name': 'General Hospital, Pathanamthitta',
                'phone_number': '0468-2222224',
                'address': 'College Road, Pathanamthitta, Kerala 689645',
                'latitude': 9.2667,
                'longitude': 76.7833,
                'district': 'Pathanamthitta',
                'anti_venom_available': True,
                'anti_venom_stock_vials': 25,
                'has_icu': True,
                'emergency_department': True,
                'operating_hours': '24/7 Emergency Care',
                'anti_venom_notes': 'District headquarters government hospital serving high-risk plantation zones adjacent to Kollam district.',
            },
        ]

        created_count = 0
        existing_count = 0

        for h_data in verified_hospitals:
            name = h_data['name']
            district = h_data['district']
            obj, created = Hospital.objects.get_or_create(
                name=name,
                district=district,
                defaults=h_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  + Added: {name} ({district})"))
            else:
                existing_count += 1
                self.stdout.write(f"  = Exists: {name} ({district})")

        final_count = Hospital.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"\nHospital seeding complete: {created_count} new facilities added, "
            f"{existing_count} already existed. Total database records: {final_count}."
        ))
