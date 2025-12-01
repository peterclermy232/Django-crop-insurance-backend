from django.core.management.base import BaseCommand
from insurance.models import Country, OrganizationType, Organization


class Command(BaseCommand):
    help = 'Seeds the database with initial data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # Create Countries
        kenya, created = Country.objects.get_or_create(
            country_code='KE',
            defaults={
                'country': 'Kenya',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created country: {kenya.country}'))

        uganda, created = Country.objects.get_or_create(
            country_code='UG',
            defaults={
                'country': 'Uganda',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created country: {uganda.country}'))

        # Create Organization Types
        insurance_type, created = OrganizationType.objects.get_or_create(
            organisation_type='Insurance Company',
            defaults={
                'organisation_type_description': 'Insurance provider organizations',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created organization type: {insurance_type.organisation_type}'))

        # Create Default Organization
        default_org, created = Organization.objects.get_or_create(
            organisation_code='DEFAULT',
            defaults={
                'country': kenya,
                'organisation_type': insurance_type,
                'organisation_name': 'Default Organization',
                'organisation_email': 'admin@default.com',
                'organisation_msisdn': '+254700000000',
                'organisation_contact': 'System Admin',
                'organisation_physical_address': 'Nairobi, Kenya',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created organization: {default_org.organisation_name}'))

        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully!'))