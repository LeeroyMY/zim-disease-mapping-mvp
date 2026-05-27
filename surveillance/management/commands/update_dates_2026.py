"""
update_dates_2026 management command.

Resets every disease case record so its date_of_onset falls within 2026
(January 1 to today). This ensures the default 'This Year' temporal filter
on the dashboard immediately shows all cases.

Run with:
    python manage.py update_dates_2026
"""

import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from surveillance.models import (
    CholeraCase, HIVCase, TBCase,
    MalariaCase, TyphoidCase, GenericDiseaseCase
)

# Year boundaries
YEAR_START = date(2026, 1, 1)
TODAY       = date.today()
TOTAL_DAYS  = (TODAY - YEAR_START).days or 1   # avoid zero if running on Jan 1


def random_2026_date():
    """Return a random date in 2026 up to today."""
    return YEAR_START + timedelta(days=random.randint(0, TOTAL_DAYS))


class Command(BaseCommand):
    help = 'Sets all case date_of_onset values to a random date within 2026'

    def handle(self, *args, **options):
        all_models = [CholeraCase, HIVCase, TBCase, MalariaCase, TyphoidCase, GenericDiseaseCase]
        grand_total = 0

        for ModelClass in all_models:
            model_name = ModelClass.__name__
            self.stdout.write('[*] Updating %s ...' % model_name)

            try:
                count = ModelClass.objects.count()
            except Exception as e:
                self.stderr.write('    SKIP %s: %s' % (model_name, e))
                continue

            if count == 0:
                self.stdout.write('    (empty, skipping)')
                continue

            batch  = []
            chunk  = 500
            offset = 0

            while offset < count:
                cases = list(ModelClass.objects.all()[offset: offset + chunk])
                for case in cases:
                    case.date_of_onset = random_2026_date()
                    batch.append(case)

                ModelClass.objects.bulk_update(batch, ['date_of_onset'])
                grand_total += len(batch)
                self.stdout.write('    Updated %d / %d records ...' % (min(offset + chunk, count), count))
                batch  = []
                offset += chunk

        self.stdout.write(self.style.SUCCESS(
            '\nDone! %d records updated to 2026 dates.' % grand_total
        ))
