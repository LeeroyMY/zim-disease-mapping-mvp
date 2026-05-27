import os
import django
import random
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from surveillance.models import CholeraCase, HIVCase, TBCase, HealthFacility

facilities = HealthFacility.objects.filter(
    Q(name__icontains='clinic') | Q(name__icontains='hospital')
)

print(f"Total clinics/hospitals available for mapping: {facilities.count()}")

def fill_missing(model_class, disease_type):
    cases = model_class.objects.all()
    count_updated = 0
    severity_choices = [c[0] for c in model_class._meta.get_field('severity').choices]
    outcome_choices = [c[0] for c in model_class._meta.get_field('outcome').choices]

    for c in cases:
        changed = False

        if not c.age:
            c.age = int(random.triangular(1, 85, 25))
            changed = True
        
        if not c.gender or c.gender == 'U':
            c.gender = random.choice(['M', 'F'])
            changed = True
            
        if not c.date_of_onset:
            days_ago = random.randint(1, 60)
            c.date_of_onset = timezone.now().date() - timedelta(days=days_ago)
            changed = True

        if not c.severity:
            c.severity = random.choice(severity_choices)
            changed = True
            
        if not c.outcome:
            c.outcome = random.choice(outcome_choices)
            changed = True
            
        if not c.variant:
            if disease_type == 'cholera': c.variant = random.choices(['O1 Ogawa', 'O1 Inaba', 'Unknown'], [0.4, 0.4, 0.2])[0]
            elif disease_type == 'tb': c.variant = random.choices(['MDR-TB', 'XDR-TB', 'Unknown'], [0.4, 0.4, 0.2])[0]
            elif disease_type == 'hiv': c.variant = random.choices(['HIV-1', 'HIV-2', 'Unknown'], [0.4, 0.4, 0.2])[0]
            changed = True

        # Ensure spatial presence
        has_coords = True
        if not c.longitude or c.longitude == 0.0 or not c.latitude or c.latitude == 0.0:
            # Assign a random coordinate in Zimbabwe if literally none exists
            c.longitude = random.uniform(25.0, 33.0)
            c.latitude = random.uniform(-22.0, -15.0)
            c.location = Point(c.longitude, c.latitude, srid=4326)
            changed = True
            
        if not c.facility:
            if facilities.exists():
                point = Point(c.longitude, c.latitude, srid=4326)
                nearest = facilities.annotate(distance=Distance('location', point)).order_by('distance').first()
                if nearest:
                    c.facility = nearest
                    changed = True

        if changed:
            c.save()
            count_updated += 1
            
    print(f"Updated {count_updated} {model_class.__name__} records to fill empty fields.")

fill_missing(CholeraCase, 'cholera')
fill_missing(HIVCase, 'hiv')
fill_missing(TBCase, 'tb')

print("Database columns fill complete.")
