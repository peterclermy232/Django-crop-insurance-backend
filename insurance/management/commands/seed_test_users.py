import secrets
import string

from django.core.management.base import BaseCommand
from django.db import transaction

from insurance.models import Organization, RoleType, User

TEST_EMAIL_DOMAIN = 'cropinsurance.test'


def generate_password(length=14):
    """Random password that satisfies the usual complexity rules."""
    alphabet = string.ascii_letters + string.digits
    while True:
        body = ''.join(secrets.choice(alphabet) for _ in range(length - 2))
        password = f"{body}@{secrets.choice(string.digits)}"
        if any(c.islower() for c in password) and any(c.isupper() for c in password):
            return password


class Command(BaseCommand):
    help = (
        'Create one QA test account per active role (emails @cropinsurance.test). '
        'Re-running resets their passwords. Use --remove to delete them before go-live.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            help='Use this password for every test account instead of random ones.',
        )
        parser.add_argument(
            '--remove',
            action='store_true',
            help='Delete all test accounts instead of creating them.',
        )

    def handle(self, *args, **options):
        test_users = User.objects.filter(user_email__iendswith=f'@{TEST_EMAIL_DOMAIN}')

        if options['remove']:
            count = test_users.count()
            test_users.delete()
            self.stdout.write(self.style.SUCCESS(f'Removed {count} test account(s).'))
            return

        organisation = Organization.objects.filter(organisation_code='DEFAULT').first()
        if organisation is None:
            self.stderr.write('Default organisation missing. Run "python manage.py seed_data" first.')
            return

        roles = RoleType.objects.filter(role_status='ACTIVE').order_by('role_id')
        if not roles.exists():
            self.stderr.write('No active roles. Run "python manage.py seed_roles" first.')
            return

        rows = []
        with transaction.atomic():
            for role in roles:
                slug = role.role_name.lower().replace('_', '-')
                email = f'{slug}@{TEST_EMAIL_DOMAIN}'
                password = options['password'] or generate_password()
                label = role.role_name.replace('_', ' ').title()

                user = User.objects.filter(user_email=email).first()
                if user is None:
                    user = User.objects.create_user(
                        user_email=email,
                        user_name=f'Test {label}',
                        password=password,
                        organisation=organisation,
                        user_role=role.role_name,
                        first_name='Test',
                        last_name=label,
                        user_status='ACTIVE',
                    )
                    action = 'created'
                else:
                    user.user_role = role.role_name
                    user.user_status = 'ACTIVE'
                    user.user_is_active = True
                    user.set_password(password)
                    user.save()
                    action = 'reset'
                rows.append((role.role_name, email, password, action))

        width = max(len(r[1]) for r in rows)
        self.stdout.write(f"\n{'ROLE':<12} {'EMAIL':<{width}}  PASSWORD")
        for role_name, email, password, action in rows:
            self.stdout.write(f'{role_name:<12} {email:<{width}}  {password}   ({action})')
        self.stdout.write(self.style.WARNING(
            '\nThese are shared QA accounts. Remove them before go-live with: '
            'python manage.py seed_test_users --remove'
        ))
