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

        # Default roles with descriptions and permissions
        default_roles = [
            {
                'role_name': 'SUPERUSER',
                'role_description': 'System administrator with full access to all features',
                'is_system_role': True,
                'permissions': {
                    'all': True  # Full access to everything
                }
            },
            {
                'role_name': 'ADMIN',
                'role_description': 'Administrator with management capabilities',
                'is_system_role': True,
                'permissions': {
                    'users': ['create', 'read', 'update', 'delete'],
                    'roles': ['create', 'read', 'update', 'delete'],
                    'farmers': ['create', 'read', 'update', 'delete'],
                    'farms': ['create', 'read', 'update', 'delete'],
                    'quotations': ['create', 'read', 'update', 'delete'],
                    'claims': ['create', 'read', 'update', 'delete'],
                    'products': ['create', 'read', 'update', 'delete'],
                    'crops': ['create', 'read', 'update', 'delete'],
                    'seasons': ['create', 'read', 'update', 'delete'],
                    'advisories': ['create', 'read', 'update', 'delete'],
                    'weather': ['create', 'read', 'update', 'delete'],
                    'inspections': ['read', 'update'],
                    'reports': ['read'],
                }
            },
            {
                'role_name': 'MANAGER',
                'role_description': 'Manager with operational oversight',
                'is_system_role': True,
                'permissions': {
                    'users': ['read'],
                    'farmers': ['read', 'update'],
                    'farms': ['read', 'update'],
                    'quotations': ['create', 'read', 'update'],
                    'claims': ['read', 'update'],
                    'products': ['read'],
                    'crops': ['read'],
                    'seasons': ['read'],
                    'advisories': ['create', 'read', 'update'],
                    'weather': ['read'],
                    'inspections': ['read', 'update'],
                    'reports': ['read'],
                }
            },
            {
                'role_name': 'ASSESSOR',
                'role_description': 'Loss assessor for claim evaluation and field inspections',
                'is_system_role': True,
                'permissions': {
                    'claims': ['read', 'update'],
                    'inspections': ['create', 'read', 'update'],
                    'farmers': ['read'],
                    'farms': ['read'],
                    'quotations': ['read'],
                    'weather': ['read'],
                    'reports': ['read'],
                }
            },
            {
                'role_name': 'AGENT',
                'role_description': 'Insurance agent for sales and customer management',
                'is_system_role': True,
                'permissions': {
                    'farmers': ['create', 'read', 'update'],
                    'farms': ['create', 'read', 'update'],
                    'quotations': ['create', 'read', 'update'],
                    'claims': ['create', 'read'],
                    'products': ['read'],
                    'crops': ['read'],
                    'seasons': ['read'],
                    'weather': ['read'],
                }
            },
            {
                'role_name': 'USER',
                'role_description': 'Standard user with basic access',
                'is_system_role': True,
                'permissions': {
                    'farmers': ['read'],
                    'farms': ['read'],
                    'quotations': ['read'],
                    'claims': ['read'],
                    'products': ['read'],
                    'crops': ['read'],
                    'seasons': ['read'],
                    'weather': ['read'],
                }
            },
            {
                'role_name': 'API_USER',
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
                    'claims': ['create', 'read'],
                    'farms': ['read'],
                    'weather': ['read'],
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
                self.stdout.write(self.style.SUCCESS(f'✓ Created role: {role.role_name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'↻ Updated role: {role.role_name}'))

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Seeding complete! Created: {created_count}, Updated: {updated_count}'
        ))