import shutil
import tempfile
import uuid
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from insurance.models import (
    Claim, Country, CoverType, Crop, Farm, Farmer, InsuranceProduct, Organization,
    OrganizationType, ProductCategory, Quotation, Season, StoredFile, User,
)
from insurance.models.inspection import ClaimPhoto, Inspection

# Smallest valid PNG
PNG = bytes.fromhex(
    '89504e470d0a1a0a0000000d4948445200000001000000010806000000'
    '1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082'
)


def make_org(code):
    country, _ = Country.objects.get_or_create(country_code='KE', defaults={'country': 'Kenya'})
    org_type, _ = OrganizationType.objects.get_or_create(organisation_type='Insurer')
    return Organization.objects.create(
        organisation_code=code, organisation_name=code, country=country, organisation_type=org_type,
        organisation_email=f'{code.lower()}@example.com', organisation_msisdn='0700000000',
        organisation_contact='Contact',
    )


class SyncTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = make_org('ORG1')
        cls.other_org = make_org('ORG2')
        cls.agent = User.objects.create_user('agent@example.com', 'Field Agent', 'pass12345',
                                             organisation=cls.org, user_role='AGENT')
        crop = Crop.objects.create(organisation=cls.org, crop='Maize')
        season = Season.objects.create(organisation=cls.org, season='Long rains')
        cover = CoverType.objects.create(cover_type='Area yield') if hasattr(CoverType, 'cover_type') \
            else CoverType.objects.create()
        category = ProductCategory.objects.create(cover_type=cover, organisation=cls.org,
                                                  product_category='Crop')
        cls.product = InsuranceProduct.objects.create(
            organisation=cls.org, product_category=category, season=season, crop=crop,
            product_name='Maize cover', average_premium_rate=Decimal('5.00'),
            sum_insured=Decimal('100000'),
        )

    def setUp(self):
        self.client.force_authenticate(self.agent)

    def sync(self, changes=None, last_sync=None, user=None):
        if user is not None:
            self.client.force_authenticate(user)
        return self.client.post('/api/v1/sync/', {
            'last_sync': last_sync, 'include_reference': True, 'changes': changes or {},
        }, format='json')

    def written_policy(self):
        farmer = Farmer.objects.create(organisation=self.org, first_name='Policy', last_name='Holder',
                                       id_number=str(uuid.uuid4())[:20], phone_number='07')
        farm = Farm.objects.create(farmer=farmer, farm_name='Insured farm', farm_size=1,
                                   unit_of_measure='ACRES')
        return Quotation.objects.create(farmer=farmer, farm=farm, insurance_product=self.product,
                                        premium_amount=5000, sum_insured=100000, status='WRITTEN',
                                        policy_number='POL-1')

    def field_visit(self, id_number='12345678'):
        """Everything an officer might capture on one offline farm visit."""
        ids = {k: str(uuid.uuid4()) for k in ('farmer', 'farm', 'quotation', 'claim', 'inspection')}
        changes = {
            'farmers': [{
                'client_uuid': ids['farmer'], 'first_name': 'Jane', 'last_name': 'Wanjiku',
                'id_number': id_number, 'phone_number': '0712345678', 'gender': 'F',
                'registration_latitude': '-1.286389', 'registration_longitude': '36.817223',
                'next_of_kin': [{'name': 'John', 'relationship': 'Spouse', 'phone_number': '0711'}],
                'bank_accounts': [{'bank_name': 'KCB', 'account_number': '001', 'account_name': 'Jane'}],
            }],
            'farms': [{
                'client_uuid': ids['farm'], 'farmer_uuid': ids['farmer'], 'farm_name': 'Shamba A',
                'farm_size': '2.50', 'unit_of_measure': 'ACRES', 'latitude': '-1.2', 'longitude': '36.8',
            }],
            'quotations': [{
                'client_uuid': ids['quotation'], 'farm_uuid': ids['farm'],
                'insurance_product': self.product.pk, 'sum_insured': '50000',
                'premium_amount': '1',  # ignored: the server computes the premium
            }],
            # Claims can only be filed on a written policy, never on a fresh quotation
            'claims': [{
                'client_uuid': ids['claim'], 'quotation': self.written_policy().pk,
                'estimated_loss_amount': '20000', 'loss_details': {'cause': 'Drought'},
            }],
            'inspections': [{
                'client_uuid': ids['inspection'], 'farm_uuid': ids['farm'],
                'inspection_type': 'LOSS_ASSESSMENT', 'status': 'COMPLETED',
                'scheduled_date': '2026-10-14', 'completed_at': '2026-10-14T10:05:00+03:00',
                'findings': {'damage_percent': 40},
            }],
        }
        return ids, changes


class OfflineUploadTests(SyncTestCase):
    def test_full_offline_visit_syncs_in_one_request(self):
        ids, changes = self.field_visit()
        response = self.sync(changes)
        self.assertEqual(response.status_code, 200, response.data)

        for name in changes:
            result = response.data['results'][name][0]
            self.assertEqual(result['status'], 'created', (name, result))
            self.assertEqual(result['client_uuid'], ids[name.rstrip('s')])

        farmer = Farmer.objects.get(client_uuid=ids['farmer'])
        self.assertEqual(farmer.organisation, self.org)
        self.assertEqual(farmer.created_by, self.agent)
        self.assertEqual(farmer.next_of_kin.count(), 1)
        self.assertEqual(farmer.bank_accounts.count(), 1)

        quotation = Quotation.objects.get(client_uuid=ids['quotation'])
        self.assertEqual(quotation.farmer, farmer)
        self.assertEqual(quotation.premium_amount, Decimal('2500.00'))  # 5% of 50,000
        self.assertEqual(quotation.status, 'OPEN')

        claim = Claim.objects.get(client_uuid=ids['claim'])
        self.assertEqual(claim.farmer, claim.quotation.farmer)
        self.assertEqual(claim.created_by, self.agent)
        self.assertTrue(claim.claim_number.startswith('CLM-'))

        inspection = Inspection.objects.get(client_uuid=ids['inspection'])
        self.assertEqual(inspection.inspector, self.agent)
        self.assertEqual(inspection.completed_at.isoformat(), '2026-10-14T07:05:00+00:00')

    def test_retrying_the_same_payload_does_not_duplicate(self):
        _, changes = self.field_visit()
        self.sync(changes)
        response = self.sync(changes)

        self.assertEqual(response.data['results']['farmers'][0]['status'], 'updated')
        # +1 farmer/farm/quotation for the pre-existing written policy the claim is filed on
        self.assertEqual(Farmer.objects.count(), 2)
        self.assertEqual(Farm.objects.count(), 2)
        self.assertEqual(Quotation.objects.count(), 2)
        self.assertEqual(Claim.objects.count(), 1)
        self.assertEqual(Inspection.objects.count(), 1)

    def test_farmer_already_registered_is_reported_as_duplicate(self):
        existing = Farmer.objects.create(organisation=self.org, first_name='A', last_name='B',
                                         id_number='999', phone_number='07')
        _, changes = self.field_visit(id_number='999')
        before = Farmer.objects.count()
        result = self.sync({'farmers': changes['farmers']}).data['results']['farmers'][0]

        self.assertEqual(result['status'], 'duplicate')
        self.assertEqual(result['server_id'], existing.pk)
        self.assertEqual(result['record']['farmer_id'], existing.pk)
        self.assertEqual(Farmer.objects.count(), before)

    def test_child_waits_when_parent_failed(self):
        _, changes = self.field_visit()
        changes['farmers'][0]['first_name'] = ''  # invalid -> farmer fails
        results = self.sync(changes).data['results']

        self.assertEqual(results['farmers'][0]['status'], 'error')
        self.assertIn('first_name', results['farmers'][0]['errors'])
        self.assertEqual(results['farms'][0]['status'], 'pending_parent')
        self.assertFalse(Farm.objects.filter(client_uuid=changes['farms'][0]['client_uuid']).exists())

    def test_claim_approved_in_office_is_locked(self):
        _, changes = self.field_visit()
        self.sync(changes)
        Claim.objects.update(status='APPROVED')

        changes['claims'][0]['estimated_loss_amount'] = '1'
        result = self.sync({'claims': changes['claims']}).data['results']['claims'][0]
        self.assertEqual(result['status'], 'locked')
        self.assertEqual(Claim.objects.get().estimated_loss_amount, Decimal('20000'))

    def test_cannot_attach_records_to_another_organisations_farmer(self):
        foreign = Farmer.objects.create(organisation=self.other_org, first_name='X', last_name='Y',
                                        id_number='555', phone_number='07')
        result = self.sync({'farms': [{
            'client_uuid': str(uuid.uuid4()), 'farmer': foreign.pk, 'farm_name': 'F',
            'farm_size': '1', 'unit_of_measure': 'ACRES',
        }]}).data['results']['farms'][0]
        self.assertEqual(result['status'], 'pending_parent')
        self.assertEqual(Farm.objects.count(), 0)

    def test_non_field_roles_cannot_sync(self):
        customer = User.objects.create_user('c@example.com', 'Customer', 'pass12345',
                                            organisation=self.org, user_role='CUSTOMER')
        self.assertEqual(self.sync(user=customer).status_code, 403)


class DownloadTests(SyncTestCase):
    def test_full_download_includes_reference_data_and_org_records_only(self):
        Farmer.objects.create(organisation=self.org, first_name='Mine', last_name='A',
                              id_number='1', phone_number='07')
        Farmer.objects.create(organisation=self.other_org, first_name='Theirs', last_name='B',
                              id_number='2', phone_number='07')
        data = self.sync().data

        self.assertEqual([f['first_name'] for f in data['updates']['farmers']], ['Mine'])
        self.assertEqual(data['reference']['insurance_products'][0]['product_id'], self.product.pk)
        self.assertIn('crops', data['reference'])

    def test_incremental_download_returns_only_changes(self):
        Farmer.objects.create(organisation=self.org, first_name='Old', last_name='A',
                              id_number='1', phone_number='07')
        server_time = self.sync().data['server_time']

        Farmer.objects.create(organisation=self.org, first_name='New', last_name='B',
                              id_number='2', phone_number='07')
        data = self.sync(last_sync=server_time).data
        self.assertEqual([f['first_name'] for f in data['updates']['farmers']], ['New'])


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PhotoUploadTests(SyncTestCase):
    @classmethod
    def tearDownClass(cls):
        from django.conf import settings
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def upload(self, **fields):
        image = SimpleUploadedFile('photo.png', PNG, content_type='image/png')
        return self.client.post('/api/v1/upload/', {'file': image, **fields}, format='multipart')

    def test_claim_photo_is_linked_and_retry_is_idempotent(self):
        ids, changes = self.field_visit()
        self.sync(changes)
        photo_uuid = str(uuid.uuid4())

        first = self.upload(entity_type='claim', entity_uuid=ids['claim'], client_uuid=photo_uuid,
                            latitude='-1.28', longitude='36.81')
        second = self.upload(entity_type='claim', entity_uuid=ids['claim'], client_uuid=photo_uuid)

        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(ClaimPhoto.objects.count(), 1)
        self.assertEqual(ClaimPhoto.objects.get().claim.client_uuid, uuid.UUID(ids['claim']))

    def test_farmer_photo_is_saved_on_farmer(self):
        ids, changes = self.field_visit()
        self.sync({'farmers': changes['farmers']})
        response = self.upload(entity_type='farmer', entity_uuid=ids['farmer'])

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(Farmer.objects.get(client_uuid=ids['farmer']).photo)

    def test_uploaded_photo_is_stored_in_database_and_served_by_signed_url(self):
        ids, changes = self.field_visit()
        self.sync({'farmers': changes['farmers']})
        url = self.upload(entity_type='farmer', entity_uuid=ids['farmer']).data['file_url']

        stored = StoredFile.objects.get()
        self.assertEqual((bytes(stored.content), stored.content_type), (PNG, 'image/png'))
        self.client.force_authenticate(None)
        response = self.client.get(url)
        self.assertEqual((response.status_code, response.content, response['Content-Type']),
                         (200, PNG, 'image/png'))
        self.assertEqual(self.client.get(url.replace('sig=', 'sig=x')).status_code, 404)
        self.assertEqual(self.client.get(url.split('?')[0]).status_code, 404)

    def test_upload_before_record_synced_asks_to_retry(self):
        response = self.upload(entity_type='claim', entity_uuid=str(uuid.uuid4()))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'pending_parent')


class RefreshRotationTests(APITestCase):
    def test_refresh_rotates_and_old_token_is_rejected(self):
        org = make_org('ORG3')
        User.objects.create_user('officer@example.com', 'Officer', 'pass12345',
                                 organisation=org, user_role='AGENT')
        login = self.client.post('/api/v1/auth/login/',
                                 {'username': 'officer@example.com', 'password': 'pass12345'}, format='json')
        old_refresh = login.data['refresh']

        refreshed = self.client.post('/api/v1/auth/token/refresh/', {'refresh': old_refresh}, format='json')
        self.assertEqual(refreshed.status_code, 200)
        self.assertTrue(refreshed.data['token'])
        self.assertNotEqual(refreshed.data['refresh'], old_refresh)

        reused = self.client.post('/api/v1/auth/token/refresh/', {'refresh': old_refresh}, format='json')
        self.assertEqual(reused.status_code, 401)
