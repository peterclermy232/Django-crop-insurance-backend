"""Users only see and reference records of their own organisation."""
from decimal import Decimal

from rest_framework.test import APITestCase

from insurance.models import (
    Advisory, AdministrativeUnit, Claim, Country, Crop, Farm, Farmer, InsuranceProduct, LossAssessor, Organization, ProductCategory,
    Quotation, RoleType, Season, User,
)
from insurance.models.insurance import CoverType
from insurance.test_sync import make_org


class TenancyTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        default = make_org('DEFAULT')
        cls.org_a, cls.org_b = make_org('ORGA'), make_org('ORGB')
        everything = ['create', 'read', 'update', 'delete']
        for role in ('ADMIN', 'AGENT', 'CUSTOMER'):
            RoleType.objects.create(organisation=default, role_name=role, is_system_role=True,
                                    permissions={'users': everything} if role == 'ADMIN' else {})
        cls.agent_a = User.objects.create_user('agent@a.com', 'Agent A', 'pass12345', organisation=cls.org_a, user_role='AGENT')
        cls.admin_a = User.objects.create_user('admin@a.com', 'Admin A', 'pass12345', organisation=cls.org_a, user_role='ADMIN')
        cls.super = User.objects.create_superuser('root@x.com', 'Root', 'pass12345')
        cls.data = {org.pk: cls.make_records(org) for org in (cls.org_a, cls.org_b)}

    @staticmethod
    def make_records(org):
        farmer = Farmer.objects.create(organisation=org, first_name='F', last_name=org.organisation_code,
                                       id_number=f'ID-{org.pk}', phone_number='07')
        farm = Farm.objects.create(farmer=farmer, farm_name='Shamba', farm_size=2, unit_of_measure='ACRES')
        crop = Crop.objects.create(organisation=org, crop='Maize')
        season = Season.objects.create(organisation=org, season='Long rains')
        category = ProductCategory.objects.create(cover_type=CoverType.objects.create(), organisation=org,
                                                  product_category='Crop')
        product = InsuranceProduct.objects.create(
            organisation=org, product_category=category, season=season, crop=crop, product_name='Cover',
            average_premium_rate=Decimal('5'), sum_insured=Decimal('1000'))
        quote = Quotation.objects.create(farmer=farmer, farm=farm, insurance_product=product,
                                         premium_amount=50, sum_insured=1000, status='WRITTEN')
        claim = Claim.objects.create(farmer=farmer, quotation=quote, claim_number=f'C-{org.pk}',
                                     estimated_loss_amount=10)
        assessor_user = User.objects.create_user(f'assessor@{org.pk}.com', 'As', 'pass12345', organisation=org,
                                                 user_role='ASSESSOR')
        assessor = LossAssessor.objects.create(user=assessor_user, organisation=org)
        return dict(farmer=farmer, farm=farm, product=product, quote=quote, claim=claim, assessor=assessor)

    def a(self, key):
        return self.data[self.org_a.pk][key]

    def b(self, key):
        return self.data[self.org_b.pk][key]

    def ids(self, url, user):
        self.client.force_authenticate(user)
        body = self.client.get(url).json()
        rows = body['results'] if isinstance(body, dict) and 'results' in body else body
        return rows

    def test_lists_only_show_own_organisation(self):
        for url, key, pk in [('/api/v1/farmers/', 'farmer', 'farmer_id'), ('/api/v1/farms/', 'farm', 'farm_id'),
                             ('/api/v1/quotations/', 'quote', 'quotation_id'), ('/api/v1/claims/', 'claim', 'claim_id'),
                             ('/api/v1/insurance_products/', 'product', 'product_id')]:
            rows = self.ids(url, self.agent_a)
            self.assertEqual({r[pk] for r in rows}, {self.a(key).pk}, url)
            self.assertEqual(len(self.ids(url, self.super)), 2, url)

    def test_other_organisations_records_are_not_found(self):
        self.client.force_authenticate(self.agent_a)
        for url in [f"/api/v1/farmers/{self.b('farmer').pk}/", f"/api/v1/farms/{self.b('farm').pk}/",
                    f"/api/v1/quotations/{self.b('quote').pk}/", f"/api/v1/claims/{self.b('claim').pk}/"]:
            self.assertEqual(self.client.get(url).status_code, 404, url)
            self.assertEqual(self.client.patch(url, {}, format='json').status_code, 404, url)
            self.assertEqual(self.client.delete(url).status_code, 404, url)

    def test_cannot_reference_other_organisations_records(self):
        self.client.force_authenticate(self.agent_a)
        r = self.client.post('/api/v1/farms/', {'farmer': self.b('farmer').pk, 'farm_name': 'X', 'farm_size': '1',
                                                'unit_of_measure': 'ACRES'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('farmer', r.json())
        r = self.client.post('/api/v1/quotations/', {'farmer': self.a('farmer').pk, 'farm': self.b('farm').pk,
                                                     'insurance_product': self.a('product').pk,
                                                     'premium_amount': '1', 'sum_insured': '10'}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.client.post(f"/api/v1/claims/{self.a('claim').pk}/assign_assessor/",
                             {'assessor_id': self.b('assessor').pk}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_new_records_belong_to_users_organisation(self):
        self.client.force_authenticate(self.agent_a)
        r = self.client.post('/api/v1/farmers/', {'first_name': 'N', 'last_name': 'W', 'id_number': 'NEW1',
                                                  'phone_number': '07'}, format='json')
        self.assertEqual(r.status_code, 201, r.json())
        self.assertEqual(Farmer.objects.get(id_number='NEW1').organisation, self.org_a)
        r = self.client.post('/api/v1/farmers/', {'first_name': 'N', 'last_name': 'W', 'id_number': 'NEW2',
                                                  'phone_number': '07', 'organisation': self.org_b.pk}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_organisations(self):
        self.assertEqual(self.client.get('/api/v1/organisations/').json()['results'], [])
        rows = self.ids('/api/v1/organisations/', self.admin_a)
        self.assertEqual([r['organisation_id'] for r in rows], [self.org_a.pk])
        self.assertEqual(self.client.post('/api/v1/organisations/', {}, format='json').status_code, 403)
        self.assertEqual(self.client.get(f'/api/v1/organisations/{self.org_b.pk}/').status_code, 404)

    def test_users_and_roles(self):
        rows = self.ids('/api/v1/users/', self.admin_a)
        self.assertTrue(rows and all(r['organisation'] == self.org_a.pk for r in rows))
        r = self.client.patch(f'/api/v1/users/{self.agent_a.pk}/', {'user_role': 'SUPERUSER'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.agent_a.refresh_from_db()
        self.assertEqual(self.agent_a.user_role, 'AGENT')

    def test_roles(self):
        RoleType.objects.create(organisation=self.org_b, role_name='B_CUSTOM')
        names = {r['role_name'] for r in self.ids('/api/v1/roles/', self.admin_a)}
        self.assertEqual(names, {'ADMIN', 'AGENT', 'CUSTOMER'})
        admin_role = RoleType.objects.get(role_name='ADMIN')
        r = self.client.patch(f'/api/v1/roles/{admin_role.pk}/', {'permissions': {}}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_dashboard_is_scoped(self):
        self.client.force_authenticate(self.agent_a)
        stats = self.client.get('/api/v1/dashboard/statistics/').json()
        self.assertEqual(stats['farmers']['total'], 1)
        self.assertEqual(stats['claims']['total'], 1)

    def test_public_registration_is_customer_only(self):
        self.client.force_authenticate(None)
        base = {'first_name': 'P', 'last_name': 'Q', 'password': 'pass12345'}
        r = self.client.post('/api/v1/auth/register/', {**base, 'email': 'x@x.com', 'user_role': 'AGENT'}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.client.post('/api/v1/auth/register/', {**base, 'email': 'y@x.com', 'organisation_id': self.org_b.pk},
                             format='json')
        self.assertIn(r.status_code, (200, 201), r.json())
        user = User.objects.get(user_email='y@x.com')
        self.assertEqual((user.organisation.organisation_code, user.user_role), ('DEFAULT', 'CUSTOMER'))

    def test_cover_types_are_shared_or_owned_by_an_organisation(self):
        self.client.force_authenticate(self.super)
        r = self.client.post('/api/v1/cover_types/', {'cover_type': 'Area yield'}, format='json')
        self.assertEqual(r.status_code, 201, r.json())
        shared = CoverType.objects.get(pk=r.json()['cover_type_id'])
        self.assertIsNone(shared.organisation_id)
        other = CoverType.objects.create(cover_type='Weather index', organisation=self.org_b)

        self.client.force_authenticate(self.admin_a)
        r = self.client.post('/api/v1/cover_types/', {'cover_type': 'Multi peril', 'organisation': self.org_b.pk},
                             format='json')
        self.assertEqual(r.status_code, 400, r.json())
        r = self.client.post('/api/v1/cover_types/', {'cover_type': 'Multi peril'}, format='json')
        self.assertEqual(r.status_code, 201, r.json())
        own = CoverType.objects.get(pk=r.json()['cover_type_id'])
        self.assertEqual(own.organisation_id, self.org_a.pk)

        names = {row['cover_type'] for row in self.ids('/api/v1/cover_types/', self.admin_a)}
        self.assertIn('Area yield', names)
        self.assertIn('Multi peril', names)
        self.assertNotIn('Weather index', names)

        self.client.force_authenticate(self.admin_a)
        self.assertEqual(self.client.patch(f'/api/v1/cover_types/{shared.pk}/', {'cover_type': 'X'},
                                           format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/v1/cover_types/{shared.pk}/').status_code, 403)
        self.assertEqual(self.client.get(f'/api/v1/cover_types/{other.pk}/').status_code, 404)
        r = self.client.patch(f'/api/v1/cover_types/{own.pk}/', {'cover_type': 'MPCI', 'organisation': None},
                              format='json')
        self.assertEqual(r.status_code, 200, r.json())
        own.refresh_from_db()
        self.assertEqual((own.cover_type, own.organisation_id), ('MPCI', self.org_a.pk))

        # Product categories can use shared and own cover types, not another organisation's
        for cover, status in ((shared, 201), (own, 201), (other, 400)):
            r = self.client.post('/api/v1/product_categories/', {'cover_type': cover.pk, 'product_category': 'Crop'},
                                 format='json')
            self.assertEqual(r.status_code, status, (cover.cover_type, r.json()))

    def test_shared_reference_data_is_read_only_for_organisations(self):
        ke = Country.objects.get(country_code='KE')
        unit = AdministrativeUnit.objects.create(country=ke, level='COUNTY', name='Nakuru')
        cases = [
            ('/api/v1/countries/', f'/api/v1/countries/{ke.pk}/', {'country': 'Kenya', 'country_code': 'KE'}),
            ('/api/v1/organisation_types/', None, {'organisation_type': 'Bank'}),
            ('/api/v1/weather_data/', None, {'location': 'Nakuru', 'data_type': 'FORECAST', 'value': '1',
                                             'recorded_at': '2026-10-01T00:00:00Z'}),
            ('/api/v1/administrative_units/', f'/api/v1/administrative_units/{unit.pk}/',
             {'country': ke.pk, 'level': 'COUNTY', 'name': 'Kisumu'}),
        ]
        for user in (self.agent_a, self.admin_a):
            self.client.force_authenticate(user)
            for list_url, detail_url, payload in cases:
                self.assertEqual(self.client.get(list_url).status_code, 200, list_url)
                self.assertEqual(self.client.post(list_url, payload, format='json').status_code, 403, list_url)
                if detail_url:
                    self.assertEqual(self.client.patch(detail_url, payload, format='json').status_code, 403, detail_url)
                    self.assertEqual(self.client.delete(detail_url).status_code, 403, detail_url)
        self.client.force_authenticate(self.super)
        for list_url, _, payload in cases[1:]:
            self.assertEqual(self.client.post(list_url, payload, format='json').status_code, 201, list_url)

    def test_advisories_belong_to_an_organisation(self):
        other = Advisory.objects.create(organisation=self.org_b, message='For B farmers')
        self.client.force_authenticate(self.agent_a)
        r = self.client.post('/api/v1/advisories/send_advisory/', {'message': 'Plant now', 'send_now': True},
                             format='json')
        self.assertEqual(r.status_code, 201, r.json())
        self.assertEqual(Advisory.objects.get(message='Plant now').organisation, self.org_a)
        rows = self.ids('/api/v1/advisories/', self.agent_a)
        self.assertEqual([r['message'] for r in rows], ['Plant now'])
        self.assertEqual(self.client.get(f'/api/v1/advisories/{other.pk}/').status_code, 404)

    def test_registration_roles_endpoint_lists_public_roles_only(self):
        self.client.force_authenticate(None)
        body = self.client.get('/api/v1/auth/register/').json()
        self.assertEqual([r['role_name'] for r in body['available_roles']], ['CUSTOMER'])
        self.assertIn('AGENT', body['restricted_roles'])
