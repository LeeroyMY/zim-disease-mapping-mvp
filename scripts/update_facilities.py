import os
os.environ['PATH'] = r"C:\Users\user\AppData\Local\Programs\OSGeo4W\bin;" + os.environ.get('PATH', '')
os.environ['PROJ_LIB'] = r'C:\Users\user\AppData\Local\Programs\OSGeo4W\share\proj'
os.environ['GDAL_DATA'] = r'C:\Users\user\AppData\Local\Programs\OSGeo4W\share\gdal'

import django
from django.db.models import Q
from django.contrib.gis.db.models.functions import Distance

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from surveillance.models import CholeraCase, HIVCase, TBCase, HealthFacility

facilities = HealthFacility.objects.filter(
    Q(name__icontains='clinic') | Q(name__icontains='hospital')
)

def update_case_facilities(model_class):
    cases = model_class.objects.all()
    updated = 0
    for case in cases:
        needs_update = False
        if not case.facility:
            needs_update = True
        else:
            name = case.facility.name.lower()
            if 'clinic' not in name and 'hospital' not in name:
                needs_update = True
                
        if needs_update and case.location:
            nearest = facilities.annotate(distance=Distance('location', case.location)).order_by('distance').first()
            if nearest:
                case.facility = nearest
                case.save()
                updated += 1
                
    print(f"Updated {updated} {model_class.__name__} cases with a valid clinic/hospital.")

update_case_facilities(CholeraCase)
update_case_facilities(HIVCase)
update_case_facilities(TBCase)

print("Finished updating facility assignments.")
