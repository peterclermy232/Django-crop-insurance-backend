"""
Loads Kenya's two administrative hierarchies into AdministrativeUnit:

  County government:   County -> Sub-County -> Ward          (kenya_county_subcounty_ward.csv)
  National government: County -> Location -> Sub-Location    (kenya_location_sublocation_2009.csv)

The location file comes from the 2009 census, so it is grouped by the old
districts and has no link to wards. Locations hang directly under the county.

Safe to re-run: existing units (including soft-deleted ones) are left alone and
only missing ones are created.
"""
import csv
import re
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from insurance.models import AdministrativeUnit as Unit, Country

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'

# Rows the census file leaves without a county, keyed by 2009 district
UNRESOLVED_DISTRICT_COUNTY = {
    'garbatulla': 'Isiolo',
    'imenti north': 'Meru',
    'imenti south': 'Meru',
    'manga': 'Nyamira',
    'suba': 'Homa Bay',
    'samia': 'Busia',
    'bunyala': 'Busia',
    'koibatek': 'Baringo',
    'loitokitok': 'Kajiado',
    'pokot central': 'West Pokot',
    'pokot north': 'West Pokot',
}

# 2009 districts that were split across two counties in 2010, keyed by (district, division)
DIVISION_COUNTY = {
    ('masaba', 'rigoma'): 'Nyamira',         # Kitutu Masaba; the rest of Masaba is Kisii
    ('masaba', 'kiamokama'): 'Kisii',
    ('masaba', 'masaba'): 'Kisii',
    ('buret', 'konoin'): 'Bomet',
    ('buret', 'kimulot'): 'Bomet',
    ('buret', 'cheptalal'): 'Bomet',
    ('thika east', 'kakuzi'): "Murang'a",
}

# Whole districts the file assigns to the wrong county
DISTRICT_COUNTY_FIX = {
    'meru south': 'Tharaka-Nithi',            # Chuka / Igambang'ombe
}


def key(name):
    """Comparison key that ignores case, spacing and punctuation."""
    return re.sub(r'[^a-z0-9]', '', (name or '').lower())


def clean(name):
    name = re.sub(r'\s+', ' ', (name or '').strip())
    name = re.sub(r'\s*Sub-\s*County$', '', name, flags=re.I)
    return name.title() if name.isupper() else name


def read_csv(path):
    if not path.exists():
        raise CommandError(f'File not found: {path}')
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


class Command(BaseCommand):
    help = "Imports Kenya's counties, sub-counties, wards, locations and sub-locations"

    def add_arguments(self, parser):
        parser.add_argument('--wards', default=str(DATA_DIR / 'kenya_county_subcounty_ward.csv'))
        parser.add_argument('--locations', default=str(DATA_DIR / 'kenya_location_sublocation_2009.csv'))
        parser.add_argument('--country-code', default='KE')

    def handle(self, *args, **opts):
        country = Country.objects.filter(country_code=opts['country_code']).first()
        if country is None:
            raise CommandError(f"Country {opts['country_code']} not found. Run seed_data first.")

        wards = self.parse_wards(read_csv(Path(opts['wards'])))
        locations = self.parse_locations(read_csv(Path(opts['locations'])), set(wards))

        with transaction.atomic():
            created = self.load(country, wards, locations)

        self.stdout.write(self.style.SUCCESS(
            'Created ' + ', '.join(f'{n} {dict(Unit.LEVEL_CHOICES)[lvl]}' for lvl, n in created.items())
            if any(created.values()) else 'Locations already up to date.'
        ))

    # ------------------------------------------------------------------ parsing

    def parse_wards(self, rows):
        """{county: {sub_county: {ward, ...}}}"""
        tree = defaultdict(lambda: defaultdict(set))
        # A few rows have no sub-county; borrow it from other wards in the same constituency
        by_constituency = {}
        for r in rows:
            if r['Sub-County'].strip():
                by_constituency.setdefault((key(r['County']), key(r['Constituency'])), clean(r['Sub-County']))
        skipped = 0
        for r in rows:
            county, ward = clean(r['County']), clean(r['Ward'])
            sub = clean(r['Sub-County']) or by_constituency.get((key(county), key(r['Constituency'])))
            if not (county and sub and ward):
                skipped += 1
                continue
            tree[county][sub].add(ward)
        if skipped:
            self.stdout.write(self.style.WARNING(f'Skipped {skipped} ward rows with no sub-county'))
        return tree

    def parse_locations(self, rows, county_names):
        """{county: {location_label: {sub_location, ...}}}"""
        counties = {key(c): c for c in county_names}
        grouped = defaultdict(lambda: defaultdict(set))   # county -> (district, location) -> subs
        skipped = 0
        for r in rows:
            district, division = clean(r['District (2009)']), clean(r['Division'])
            county = (DIVISION_COUNTY.get((district.lower(), division.lower()))
                      or DISTRICT_COUNTY_FIX.get(district.lower())
                      or clean(r['County'])
                      or UNRESOLVED_DISTRICT_COUNTY.get(district.lower()))
            county = counties.get(key(county))   # use the ward file's spelling
            location, sub = clean(r['Location']), clean(r['Sub-location'])
            if not (county and location and sub):
                skipped += 1
                continue
            grouped[county][(district, location)].add(sub)
        if skipped:
            self.stdout.write(self.style.WARNING(f'Skipped {skipped} sub-location rows with no county'))

        # The same location name can occur under two old districts of one county;
        # only then add the district to tell them apart.
        tree = defaultdict(dict)
        for county, locs in grouped.items():
            name_count = defaultdict(int)
            for _, loc in locs:
                name_count[key(loc)] += 1
            for (district, loc), subs in locs.items():
                label = f'{loc} ({district})' if name_count[key(loc)] > 1 else loc
                tree[county].setdefault(label, set()).update(subs)
        return tree

    # ------------------------------------------------------------------ loading

    def load(self, country, wards, locations):
        existing = {(u.parent_id, u.level, key(u.name)): u for u in Unit.objects.filter(country=country)}
        created = defaultdict(int)

        def get_or_add(parent, level, names):
            """Returns {name: unit} for names under parent, creating the missing ones in bulk."""
            parent_id = parent.pk if parent else None
            found, new = {}, []
            for name in sorted(names):
                unit = existing.get((parent_id, level, key(name)))
                if unit is None:
                    unit = Unit(country=country, parent=parent, level=level, name=name)
                    existing[(parent_id, level, key(name))] = unit
                    new.append(unit)
                found[name] = unit
            if new:
                Unit.objects.bulk_create(new)   # sets pk on PostgreSQL and SQLite 3.35+
                created[level] += len(new)
            return found

        county_units = get_or_add(None, Unit.COUNTY, set(wards) | set(locations))
        for county, unit in county_units.items():
            subs = get_or_add(unit, Unit.SUB_COUNTY, wards.get(county, {}))
            for sub_name, sub_unit in subs.items():
                get_or_add(sub_unit, Unit.WARD, wards[county][sub_name])
            locs = get_or_add(unit, Unit.LOCATION, locations.get(county, {}))
            for loc_name, loc_unit in locs.items():
                get_or_add(loc_unit, Unit.SUB_LOCATION, locations[county][loc_name])
        return created
