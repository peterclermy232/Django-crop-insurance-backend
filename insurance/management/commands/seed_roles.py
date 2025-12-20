# Create this file: management/commands/seed_roles.py

from django.core.management.base import BaseCommand
from insurance.models import RoleType, Organization


class Command(BaseCommand):
    help = 'Seeds default role types into the database'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding default roles...')

        # Get default organization
        try:
            default_org = Organization.objects.get(organisation_code='DEFAULT')
        except Organization.DoesNotExist:
            self.stdout.write(self.style.ERROR('Default organization not found. Please run seed_data first.'))
            return

        # Default roles with descriptions
        default_roles = [
            {
                'role_name': 'SUPERUSER',
                'role_description': 'System administrator with full access to all features',
                'is_system_role': True,
                'permissions': {
                    'all': True
                }
            },
            {
                'role_name': 'ADMIN',
                'role_description': 'Administrator with management capabilities',
                'is_system_role': True,
                'permissions': {
                    'users': ['create', 'read', 'update', 'delete'],
                    'roles': ['read'],
                    'farmers': ['create', 'read', 'update', 'delete'],
                    'quotations': ['create', 'read', 'update', 'delete'],
                    'claims': ['create', 'read', 'update', 'delete']
                }
            },
            {
                'role_name': 'MANAGER',
                'role_description': 'Manager with operational oversight',
                'is_system_role': True,
                'permissions': {
                    'users': ['read'],
                    'farmers': ['read', 'update'],
                    'quotations': ['read', 'update'],
                    'claims': ['read', 'update']
                }
            },
            {
                'role_name': 'ASSESSOR',
                'role_description': 'Loss assessor for claim evaluation',
                'is_system_role': True,
                'permissions': {
                    'claims': ['read', 'update'],
                    'farmers': ['read'],
                    'quotations': ['read']
                }
            },
            {
                'role_name': 'USER',
                'role_description': 'Standard user with basic access',
                'is_system_role': True,
                'permissions': {
                    'farmers': ['read'],
                    'quotations': ['read'],
                    'claims': ['read']
                }
            },
            {
                'role_name': 'API USER',
                'role_description': 'API integration user',
                'is_system_role': True,
                'permissions': {
                    'api': ['read', 'write']
                }
            },
            {
                'role_name': 'CUSTOMER',
                'role_description': 'Customer/farmer portal access',
                'is_system_role': True,
                'permissions': {
                    'profile': ['read', 'update'],
                    'quotations': ['read'],
                    'claims': ['create', 'read']
                }
            }
        ]

        created_count = 0
        updated_count = 0

        for role_data in default_roles:
            role, created = RoleType.objects.update_or_create(
                role_name=role_data['role_name'],
                defaults={
                    'organisation': default_org,
                    'role_description': role_data['role_description'],
                    'role_status': 'ACTIVE',
                    'is_system_role': role_data['is_system_role'],
                    'permissions': role_data['permissions']
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created role: {role.role_name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'Updated role: {role.role_name}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nSeeding complete! Created: {created_count}, Updated: {updated_count}'
        ))