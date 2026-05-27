import os, django
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from surveillance.models import AdministrativeBoundary
levels = AdministrativeBoundary.objects.values_list('level', flat=True).distinct()
print(f"Distinct boundary levels in DB: {list(levels)}")

wards = AdministrativeBoundary.objects.filter(level__iexact='ward').count()
print(f"Total wards: {wards}")
