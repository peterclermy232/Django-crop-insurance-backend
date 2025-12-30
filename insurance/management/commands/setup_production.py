from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Setup production database with migrations and seed data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting production setup...'))
        
        # Run migrations
        self.stdout.write('Running migrations...')
        call_command('migrate', '--noinput')
        self.stdout.write(self.style.SUCCESS('✓ Migrations complete'))
        
        # Seed data
        try:
            self.stdout.write('Seeding base data...')
            call_command('seed_data')
            self.stdout.write(self.style.SUCCESS('✓ Base data seeded'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Base data already exists or error: {e}'))
        
        # Seed roles
        try:
            self.stdout.write('Seeding roles...')
            call_command('seed_roles')
            self.stdout.write(self.style.SUCCESS('✓ Roles seeded'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Roles already exist or error: {e}'))
        
        # Collect static files
        self.stdout.write('Collecting static files...')
        call_command('collectstatic', '--noinput', '--clear')
        self.stdout.write(self.style.SUCCESS('✓ Static files collected'))
        
        self.stdout.write(self.style.SUCCESS('\n✓ Production setup complete!'))