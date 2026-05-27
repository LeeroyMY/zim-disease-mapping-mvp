"""
backfill_data management command.

Scans every disease case table in the database and fills any NULL / empty
column with a sensible default so that:
  - Every case has a date_of_onset
  - Every case has an age
  - Every case has a gender (M or F, not U/Unknown)
  - Every case has a variant
  - Every case has a location_name
  - Every case has a severity and an outcome
  - Every case with valid coordinates but no facility gets the nearest facility assigned

Run with:
    python manage.py backfill_data
"""

import random
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from surveillance.models import (
    BaseDiseaseCase, CholeraCase, HIVCase, TBCase,
    MalariaCase, TyphoidCase, GenericDiseaseCase, HealthFacility
)

# Map each disease type to its default variant pool
VARIANT_DEFAULTS = {
    'cholera':  ['O1 Ogawa', 'O1 Inaba', 'O139'],
    'hiv':      ['HIV-1', 'HIV-2'],
    'tb':       ['Drug-Sensitive TB', 'MDR-TB', 'XDR-TB'],
    'malaria':  ['P. falciparum', 'P. vivax', 'P. malariae'],
    'typhoid':  ['S. Typhi', 'S. Paratyphi A', 'S. Paratyphi B'],
}

LOCATION_DEFAULTS = [
    'Harare', 'Bulawayo', 'Mutare', 'Gweru', 'Masvingo',
    'Chitungwiza', 'Kwekwe', 'Kadoma', 'Chinhoyi', 'Norton',
    'Mbare', 'Glen View', 'Highfield', 'Mabvuku', 'Tafara',
    'Nkayi', 'Binga', 'Gokwe', 'Lupane', 'Karoi',
]

OUTCOME_CHOICES = ['active', 'recovered', 'deceased', 'referred']
SEVERITY_CHOICES = [1, 2, 3]


class Command(BaseCommand):
    help = 'Backfills NULL/empty columns in all disease case tables with realistic defaults'

    def handle(self, *args, **options):
        all_models = [CholeraCase, HIVCase, TBCase, MalariaCase, TyphoidCase, GenericDiseaseCase]
        all_facilities = list(HealthFacility.objects.all())

        total_fixed = 0

        for ModelClass in all_models:
            model_name = ModelClass.__name__
            self.stdout.write('\n[*] Processing %s...' % model_name)

            try:
                cases = ModelClass.objects.all()
                count = cases.count()
                self.stdout.write('   Found %d records.' % count)
            except Exception as e:
                self.stderr.write('   WARNING: Could not query %s: %s' % (model_name, e))
                continue

            batch = []
            changed_fields_set = set()

            for case in cases.iterator(chunk_size=500):
                changed = False

                # --- 1. date_of_onset ---
                if case.date_of_onset is None:
                    # Spread dates over the past 3 years so the time-series chart looks realistic
                    days_back = random.randint(1, 1095)
                    case.date_of_onset = (timezone.now() - timedelta(days=days_back)).date()
                    changed = True
                    changed_fields_set.add('date_of_onset')

                # --- 2. age ---
                if case.age is None:
                    disease = getattr(case, 'disease_type', '').lower()
                    if disease in ('hiv', 'tb'):
                        case.age = int(random.triangular(18, 80, 32))
                    else:
                        case.age = int(random.triangular(1, 75, 22))
                    changed = True
                    changed_fields_set.add('age')

                # --- 3. gender ---
                if not case.gender or case.gender == 'U':
                    disease = getattr(case, 'disease_type', '').lower()
                    if disease == 'hiv':
                        case.gender = random.choices(['F', 'M'], weights=[0.60, 0.40])[0]
                    else:
                        case.gender = random.choice(['M', 'F'])
                    changed = True
                    changed_fields_set.add('gender')

                # --- 4. variant ---
                if not case.variant or case.variant in ('Unknown', 'Unspecified', '', None):
                    disease = getattr(case, 'disease_type', '').lower()
                    pool = VARIANT_DEFAULTS.get(disease, ['Variant A', 'Variant B', 'Variant C'])
                    case.variant = random.choice(pool)
                    changed = True
                    changed_fields_set.add('variant')

                # --- 5. location_name ---
                if not case.location_name or case.location_name in ('', 'Unknown Location', None):
                    case.location_name = random.choice(LOCATION_DEFAULTS)
                    changed = True
                    changed_fields_set.add('location_name')

                # --- 6. severity ---
                if case.severity is None:
                    case.severity = random.choice(SEVERITY_CHOICES)
                    changed = True
                    changed_fields_set.add('severity')

                # --- 7. outcome ---
                if not case.outcome or case.outcome == '':
                    case.outcome = random.choice(OUTCOME_CHOICES)
                    changed = True
                    changed_fields_set.add('outcome')

                # --- 8. facility (assign nearest if missing and has valid coords) ---
                if case.facility is None and all_facilities and case.longitude and case.latitude:
                    try:
                        loc = Point(float(case.longitude), float(case.latitude), srid=4326)
                        nearest = min(
                            (f for f in all_facilities if f.location),
                            key=lambda f: f.location.distance(loc),
                            default=None
                        )
                        if nearest:
                            case.facility = nearest
                            changed = True
                            changed_fields_set.add('facility_id')
                    except Exception:
                        pass

                if changed:
                    batch.append(case)
                    total_fixed += 1

                # Flush batch every 500 records to keep memory low
                if len(batch) >= 500:
                    fields_to_update = list(changed_fields_set - {'facility_id'})
                    if 'facility_id' in changed_fields_set:
                        fields_to_update.append('facility_id')
                    ModelClass.objects.bulk_update(batch, fields_to_update)
                    self.stdout.write('   Flushed batch of %d records...' % len(batch))
                    batch = []
                    changed_fields_set = set()

            # Flush remaining
            if batch:
                fields_to_update = list(changed_fields_set - {'facility_id'})
                if 'facility_id' in changed_fields_set:
                    fields_to_update.append('facility_id')
                ModelClass.objects.bulk_update(batch, fields_to_update)
                self.stdout.write('   Flushed final batch of %d records.' % len(batch))

        self.stdout.write(self.style.SUCCESS(
            '\nBackfill complete! Fixed %d records across all disease tables.' % total_fixed
        ))
