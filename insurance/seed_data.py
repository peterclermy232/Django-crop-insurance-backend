from django.core.management.base import BaseCommand
from insurance.models import Country, OrganizationType, Organization

class Command(BaseCommand):
    help = 'Seed initial data into the database'

    def handle(self, *args, **kwargs):
        Country.objects.get_or_create(country='Kenya', country_code='KE')
        OrganizationType.objects.get_or_create(organisation_type='Insurance Company')
        self.stdout.write(self.style.SUCCESS('Seed data created successfully'))
