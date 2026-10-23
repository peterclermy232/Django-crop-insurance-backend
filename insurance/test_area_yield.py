"""Area yield index cover: product terms, sales rules, approval and payouts."""
from decimal import Decimal

from rest_framework.test import APITestCase

from insurance.models import (
    AdministrativeUnit, AreaYield, Claim, Country, CoverType, Crop, Farm, Farmer, InsuranceProduct,
    ProductCategory, Quotation, Season, User,
)
from insurance.test_sync import make_org


class AreaYieldTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = make_org('AYI')
        ke = Country.objects.get(country_code='KE')
        county = AdministrativeUnit.objects.create(country=ke, level='COUNTY', name='Trans Nzoia')
        sub_county = AdministrativeUnit.objects.create(country=ke, parent=county, level='SUB_COUNTY', name='Kiminini')
        cls.ward = AdministrativeUnit.objects.create(country=ke, parent=sub_county, level='WARD', name='Waitaluk')
        cls.other_ward = AdministrativeUnit.objects.create(country=ke, parent=sub_county, level='WARD', name='Sirende')

        cls.admin = User.objects.create_user('admin@ayi.com', 'Admin One', 'pass12345', organisation=cls.org,
                                             user_role='ADMIN')
        cls.checker = User.objects.create_user('checker@ayi.com', 'Admin Two', 'pass12345', organisation=cls.org,
                                               user_role='ADMIN')
        cls.agent = User.objects.create_user('agent@ayi.com', 'Agent', 'pass12345', organisation=cls.org,
                                             user_role='AGENT')

        cls.crop = Crop.objects.create(organisation=cls.org, crop='Maize')
        cls.season = Season.objects.create(organisation=cls.org, season='Long rains 2027')
        cls.cover = CoverType.objects.create(cover_type='Area Yield Index', calculation_method=CoverType.AREA_YIELD)
        cls.category = ProductCategory.objects.create(cover_type=cls.cover, organisation=cls.org,
                                                      product_category='Maize AYI')
        cls.product = InsuranceProduct.objects.create(
            organisation=cls.org, product_category=cls.category, season=cls.season, crop=cls.crop,
            product_name='Maize Area Yield', average_premium_rate=Decimal('5'), sum_insured=Decimal('20000'),
            area_level='WARD', coverage_level=Decimal('70'), yield_unit='bags/acre')

        cls.policy = cls.make_policy('Wanjiku', cls.ward, Decimal('100000'))
        cls.neighbour = cls.make_policy('Otieno', cls.other_ward, Decimal('50000'))

    @classmethod
    def make_policy(cls, name, unit, sum_insured):
        farmer = Farmer.objects.create(organisation=cls.org, first_name=name, last_name='F',
                                       id_number=f'ID-{name}', phone_number='07')
        farm = Farm.objects.create(farmer=farmer, farm_name=f'{name} shamba', farm_size=5,
                                   unit_of_measure='ACRES', administrative_unit=unit)
        return Quotation.objects.create(farmer=farmer, farm=farm, insurance_product=cls.product,
                                        premium_amount=5000, sum_insured=sum_insured, status='WRITTEN',
                                        policy_number=f'POL-{name}')

    def enter_yield(self, actual='15', unit=None):
        self.client.force_authenticate(self.admin)
        r = self.client.post('/api/v1/area_yields/', {
            'crop': self.crop.pk, 'season': self.season.pk,
            'administrative_unit': (unit or self.ward).pk, 'expected_yield': '30', 'actual_yield': actual,
            'yield_unit': 'bags/acre', 'source': 'County crop-cut survey',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.json())
        return r.json()['area_yield_id']

    def approve(self, pk):
        self.client.force_authenticate(self.checker)
        r = self.client.post(f'/api/v1/area_yields/{pk}/approve/')
        self.assertEqual(r.status_code, 200, r.json())

    def test_payout_follows_area_yield_and_needs_two_admins(self):
        pk = self.enter_yield()
        area_yield = AreaYield.objects.get(pk=pk)
        self.assertEqual((area_yield.organisation, area_yield.entered_by), (self.org, self.admin))

        # The admin who entered the figures can't approve them, and agents can't touch them
        self.assertEqual(self.client.post(f'/api/v1/area_yields/{pk}/approve/').status_code, 403)
        self.assertEqual(self.client.post(f'/api/v1/area_yields/{pk}/calculate_payouts/').status_code, 400)
        self.client.force_authenticate(self.agent)
        self.assertEqual(self.client.get('/api/v1/area_yields/').status_code, 200)
        self.assertEqual(self.client.post(f'/api/v1/area_yields/{pk}/approve/').status_code, 403)

        self.approve(pk)
        r = self.client.patch(f'/api/v1/area_yields/{pk}/', {'actual_yield': '25'}, format='json')
        self.assertEqual(r.status_code, 400)

        # Preview: 30 x 70% = 21 guaranteed, 15 measured -> (21 - 15) / 21 = 28.57% of 100,000
        r = self.client.post(f'/api/v1/area_yields/{pk}/calculate_payouts/', {'preview': True}, format='json')
        self.assertEqual(r.status_code, 200, r.json())
        body = r.json()
        self.assertEqual((body['policies'], body['claims_created'], body['total_payout']), (1, 0, '28571.43'))
        row = body['rows'][0]
        self.assertEqual((row['guaranteed_yield'], row['payout_percent'], row['payout'], row['outcome']),
                         ('21.00', '28.57', '28571.43', 'WILL_CREATE_CLAIM'))
        self.assertFalse(Claim.objects.exists())

        r = self.client.post(f'/api/v1/area_yields/{pk}/calculate_payouts/', {}, format='json')
        self.assertEqual(r.status_code, 201, r.json())
        claim = Claim.objects.get()
        self.assertEqual((claim.quotation, claim.estimated_loss_amount, claim.status),
                         (self.policy, Decimal('28571.43'), 'OPEN'))
        self.assertEqual(claim.loss_details['calculation_method'], CoverType.AREA_YIELD)
        self.assertIsNotNone(AreaYield.objects.get(pk=pk).payouts_calculated_at)
        detail = self.client.get(f'/api/v1/claims/{claim.pk}/').json()
        self.assertEqual(detail['calculation_method'], CoverType.AREA_YIELD)

        # Running it again doesn't pay twice
        r = self.client.post(f'/api/v1/area_yields/{pk}/calculate_payouts/', {}, format='json')
        self.assertEqual(r.json()['rows'][0]['outcome'], 'ALREADY_CLAIMED')
        self.assertEqual(Claim.objects.count(), 1)

    def test_no_payout_when_area_yield_is_above_threshold(self):
        pk = self.enter_yield(actual='22', unit=self.other_ward)
        self.approve(pk)
        r = self.client.post(f'/api/v1/area_yields/{pk}/calculate_payouts/', {}, format='json')
        self.assertEqual(r.json()['rows'][0]['outcome'], 'NO_PAYOUT')
        self.assertEqual(r.json()['rows'][0]['farmer_name'], 'Otieno F')
        self.assertFalse(Claim.objects.exists())

    def test_payout_is_capped(self):
        self.product.max_payout_percent = Decimal('50')
        self.product.save()
        pk = self.enter_yield(actual='0')
        self.approve(pk)
        r = self.client.post(f'/api/v1/area_yields/{pk}/calculate_payouts/', {'preview': True}, format='json')
        self.assertEqual(r.json()['rows'][0]['payout'], '50000.00')

    def test_area_yield_policies_cannot_be_claimed_individually(self):
        self.client.force_authenticate(self.agent)
        r = self.client.post('/api/v1/claims/', {'farmer': self.policy.farmer.pk, 'quotation': self.policy.pk,
                                                 'estimated_loss_amount': '1000'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('area yield', str(r.json()).lower())

    def test_area_yield_product_needs_terms_and_farm_needs_ward(self):
        self.client.force_authenticate(self.admin)
        r = self.client.post('/api/v1/insurance_products/', {
            'product_category': self.category.pk, 'season': self.season.pk, 'crop': self.crop.pk,
            'product_name': 'No terms', 'average_premium_rate': '5', 'sum_insured': '1000',
        }, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(set(r.json()), {'area_level', 'coverage_level', 'yield_unit'})

        farmer = Farmer.objects.create(organisation=self.org, first_name='No', last_name='Ward',
                                       id_number='ID-nw', phone_number='07')
        farm = Farm.objects.create(farmer=farmer, farm_name='Unmapped', farm_size=1, unit_of_measure='ACRES')
        quote = {'farmer': farmer.pk, 'farm': farm.pk, 'insurance_product': self.product.pk,
                 'premium_amount': '100', 'sum_insured': '2000'}
        r = self.client.post('/api/v1/quotations/', quote, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('ward', str(r.json()).lower())

        farm.administrative_unit = self.ward
        farm.save()
        r = self.client.post('/api/v1/quotations/', quote, format='json')
        self.assertEqual(r.status_code, 201, r.json())
        self.assertEqual(r.json()['calculation_method'], CoverType.AREA_YIELD)
        self.assertIn('average yield of the whole ward', r.json()['basis_risk_notice'])

    def test_cover_type_method_is_fixed_once_used(self):
        self.client.force_authenticate(User.objects.create_superuser('root@ayi.com', 'Root', 'pass12345',
                                                                     organisation=self.org))
        r = self.client.patch(f'/api/v1/cover_types/{self.cover.pk}/',
                              {'calculation_method': CoverType.INDIVIDUAL_FARM}, format='json')
        self.assertEqual(r.status_code, 400)
