from django.core.management.base import BaseCommand
from laboratories.models import Category, Laboratory, Review, User


class Command(BaseCommand):
    help = 'Populate sample laboratories and categories for TestLab Finder'

    def handle(self, *args, **options):
        categories = [
            ('Food Testing', 'Food testing labs ensure safety and compliance for consumables.'),
            ('Water Testing', 'Water quality and contamination assessment services.'),
            ('Air Testing', 'Indoor and outdoor air quality monitoring.'),
            ('Product Quality Testing', 'End-product quality and performance testing.'),
            ('Daily Consumer Product Testing', 'Testing for household and personal-care products.'),
            ('Office Environment Testing', 'Workplace environment analysis and compliance.'),
            ('Office Voice/Noise Testing', 'Noise and acoustic testing for office spaces.'),
            ('Chemical Testing', 'Chemical composition and contamination analysis.'),
            ('Electronics Testing', 'Electronic component and device validation.'),
            ('Industrial Testing', 'Manufacturing and industrial process testing.'),
        ]

        for name, description in categories:
            Category.objects.get_or_create(category_name=name, defaults={'description': description})

        owner, _ = User.objects.get_or_create(
            username='companyadmin',
            defaults={
                'email': 'company@example.com',
                'name': 'Sample Company',
                'role': 'company',
                'is_active': True,
                'is_verified': True,
            },
        )

        labs = [
            {
                'name': 'MetroLab Diagnostics',
                'description': 'A leading lab focused on food and water testing.',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'address': '34 Park Avenue',
                'phone': '9876543210',
                'email': 'info@metrolab.com',
                'website': 'https://metrolab.example.com',
                'accreditation': 'ISO 17025',
                'is_approved': True,
                'categories': ['Food Testing', 'Water Testing'],
            },
            {
                'name': 'Green Air Labs',
                'description': 'Professional environmental testing for office and industrial spaces.',
                'city': 'Bengaluru',
                'state': 'Karnataka',
                'address': '78 Tech Park Road',
                'phone': '9812345678',
                'email': 'hello@greenairlabs.com',
                'website': 'https://greenairlabs.example.com',
                'accreditation': 'NABL',
                'is_approved': True,
                'categories': ['Air Testing', 'Office Environment Testing'],
            },
        ]

        for data in labs:
            lab, created = Laboratory.objects.get_or_create(
                name=data['name'],
                defaults={
                    'owner': owner,
                    'description': data['description'],
                    'city': data['city'],
                    'state': data['state'],
                    'address': data['address'],
                    'phone': data['phone'],
                    'email': data['email'],
                    'website': data['website'],
                    'accreditation': data['accreditation'],
                    'is_approved': data['is_approved'],
                },
            )
            if created:
                for category_name in data['categories']:
                    lab.categories.add(Category.objects.get(category_name=category_name))
                Review.objects.get_or_create(
                    laboratory=lab,
                    user=owner,
                    defaults={'rating': 5, 'review_text': 'Excellent service and quick reports.'},
                )

        self.stdout.write(self.style.SUCCESS('Sample data populated.'))
