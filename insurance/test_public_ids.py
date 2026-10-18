"""Records can be addressed by random public UUIDs instead of guessable numbers."""
import uuid

from django.test import override_settings
from rest_framework.test import APITestCase

from insurance.models import Farm, Farmer, User
from insurance.test_tenancy import TenancyTestCase

UUID = {'HTTP_X_ID_FORMAT': 'uuid'}


def is_uuid(value):
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


class PublicIdTestCase(APITestCase):
    setUpTestData = TenancyTestCase.__dict__['setUpTestData']
    make_records = TenancyTestCase.__dict__['make_records']

    def setUp(self):
        self.client.force_authenticate(self.agent_a)
        self.farmer = Farmer.objects.get(organisation=self.org_a)
        self.farm = Farm.objects.get(farmer=self.farmer)

    def test_numeric_by_default(self):
        farm = self.client.get(f'/api/v1/farms/{self.farm.pk}/').json()
        self.assertEqual((farm['farm_id'], farm['farmer']), (self.farm.pk, self.farmer.pk))

    def test_uuid_format_replaces_ids_and_relations(self):
        farm = self.client.get(f'/api/v1/farms/{self.farm.public_id}/', **UUID).json()
        self.assertEqual(farm['farm_id'], str(self.farm.public_id))
        self.assertEqual(farm['farmer'], str(self.farmer.public_id))
        farmer = self.client.get(f'/api/v1/farmers/{self.farmer.public_id}/', **UUID).json()
        self.assertEqual(farmer['farmer_id'], str(self.farmer.public_id))
        self.assertEqual(farmer['organisation'], str(self.org_a.public_id))
        self.assertTrue(farmer['farms'] and all(is_uuid(f['farm_id']) for f in farmer['farms']))
        rows = self.client.get('/api/v1/quotations/', **UUID).json()['results']
        self.assertTrue(all(is_uuid(r[k]) for r in rows for k in ('quotation_id', 'farmer', 'farm', 'insurance_product')))

    def test_relations_and_filters_accept_uuids(self):
        r = self.client.post('/api/v1/farms/', {'farmer': str(self.farmer.public_id), 'farm_name': 'New',
                                                'farm_size': '1', 'unit_of_measure': 'ACRES'}, format='json', **UUID)
        self.assertEqual(r.status_code, 201, r.json())
        self.assertEqual(r.json()['farmer'], str(self.farmer.public_id))
        rows = self.client.get(f'/api/v1/farms/?farmer_id={self.farmer.public_id}', **UUID).json()['results']
        self.assertEqual(len(rows), 2)
        self.assertEqual(self.client.get(f'/api/v1/farms/?farmer_id={uuid.uuid4()}').json()['results'], [])

    def test_other_organisations_uuid_is_not_found(self):
        other = Farmer.objects.get(organisation=self.org_b)
        self.assertEqual(self.client.get(f'/api/v1/farmers/{other.public_id}/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/v1/farmers/{uuid.uuid4()}/').status_code, 404)
        self.assertEqual(self.client.get('/api/v1/farmers/not-an-id/').status_code, 404)

    @override_settings(PUBLIC_IDS_DEFAULT='uuid', ALLOW_NUMERIC_IDS=False)
    def test_locked_down_mode(self):
        self.assertEqual(self.client.get(f'/api/v1/farmers/{self.farmer.pk}/').status_code, 404)
        farmer = self.client.get(f'/api/v1/farmers/{self.farmer.public_id}/').json()
        self.assertEqual(farmer['farmer_id'], str(self.farmer.public_id))
        # Asking for numbers doesn't bring them back
        farmer = self.client.get(f'/api/v1/farmers/{self.farmer.public_id}/', HTTP_X_ID_FORMAT='numeric').json()
        self.assertTrue(is_uuid(farmer['farmer_id']))
        r = self.client.post('/api/v1/farms/', {'farmer': self.farmer.pk, 'farm_name': 'X', 'farm_size': '1',
                                                'unit_of_measure': 'ACRES'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_users_have_public_ids(self):
        self.client.force_authenticate(self.admin_a)
        me = self.client.get(f'/api/v1/users/{self.admin_a.public_id}/', **UUID).json()
        self.assertEqual(me['user_id'], str(self.admin_a.public_id))
        self.assertEqual(me['organisation'], str(self.org_a.public_id))


class SyncPublicIdTestCase(APITestCase):
    setUpTestData = TenancyTestCase.__dict__['setUpTestData']
    make_records = TenancyTestCase.__dict__['make_records']

    def sync(self, changes, **headers):
        self.client.force_authenticate(self.agent_a)
        return self.client.post('/api/v1/sync/', {'last_sync': None, 'changes': changes}, format='json', **headers).json()

    def check_round_trip(self, **headers):
        farmer = Farmer.objects.get(organisation=self.org_a)
        product = farmer.quotation_set.first().insurance_product
        body = self.sync({
            'farms': [{'client_uuid': str(uuid.uuid4()), 'farmer': str(farmer.public_id), 'farm_name': 'Synced',
                       'farm_size': '1.00', 'unit_of_measure': 'ACRES'}],
        }, **headers)
        result = body['results']['farms'][0]
        self.assertEqual(result['status'], 'created', result)
        farm = Farm.objects.get(farm_name='Synced')
        self.assertEqual(result['server_id'], str(farm.public_id))
        body = self.sync({
            'quotations': [{'client_uuid': str(uuid.uuid4()), 'farm': result['server_id'],
                            'insurance_product': str(product.public_id), 'sum_insured': '1000.00'}],
        }, **headers)
        self.assertEqual(body['results']['quotations'][0]['status'], 'created', body['results'])
        self.assertTrue(all(is_uuid(f['farmer_id']) for f in body['updates']['farmers']))
        self.assertTrue(all(is_uuid(p['product_id']) for p in body['reference']['insurance_products']))

    def test_sync_with_uuid_header(self):
        self.check_round_trip(**UUID)

    @override_settings(PUBLIC_IDS_DEFAULT='uuid', ALLOW_NUMERIC_IDS=False)
    def test_sync_when_locked_down(self):
        self.check_round_trip()

    def test_other_organisations_product_is_rejected(self):
        farm = Farm.objects.get(farmer__organisation=self.org_a)
        other_product = Farmer.objects.get(organisation=self.org_b).quotation_set.first().insurance_product
        body = self.sync({'quotations': [{'client_uuid': str(uuid.uuid4()), 'farm': str(farm.public_id),
                                          'insurance_product': str(other_product.public_id), 'sum_insured': '10'}]}, **UUID)
        self.assertEqual(body['results']['quotations'][0]['status'], 'error')
