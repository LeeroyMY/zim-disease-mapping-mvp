import os
os.environ['PATH'] = r"C:\Users\user\AppData\Local\Programs\OSGeo4W\bin;" + os.environ.get('PATH', '')
os.environ['PROJ_LIB'] = r'C:\Users\user\AppData\Local\Programs\OSGeo4W\share\proj'
os.environ['GDAL_DATA'] = r'C:\Users\user\AppData\Local\Programs\OSGeo4W\share\gdal'

import django
import random
from datetime import timedelta
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.db.models import Q
from django.contrib.gis.db.models.functions import Distance

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from surveillance.models import CholeraCase, HealthFacility

facilities = HealthFacility.objects.filter(
    Q(name__icontains='clinic') | Q(name__icontains='hospital')
)

if not facilities.exists():
    print("No facilities found!")
    exit()

print("Generating 150 Cholera cases...")
for _ in range(150):
    lon = random.uniform(28.0, 32.0)
    lat = random.uniform(-20.0, -16.0)
    pt = Point(lon, lat, srid=4326)
    
    nearest = facilities.annotate(distance=Distance('location', pt)).order_by('distance').first()
    
    variant = random.choices(['O1 Ogawa', 'O1 Inaba', 'Unknown'], [0.4, 0.4, 0.2])[0]
    
    CholeraCase.objects.create(
        disease_type='cholera',
        variant=variant,
        age=random.randint(5, 65),
        gender=random.choice(['M', 'F']),
        date_of_onset=timezone.now().date() - timedelta(days=random.randint(1, 40)),
        location_name='Generated Location',
        location=pt,
        longitude=lon,
        latitude=lat,
        facility=nearest,
        severity=random.choice([1, 2, 3]),
        outcome=random.choice(['active', 'recovered'])
    )

print(f"Generated successfully. Handled: {CholeraCase.objects.count()} total cholera cases.")
