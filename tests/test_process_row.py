import os, django
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from surveillance.views import _process_row
from surveillance.models import CholeraCase

CholeraCase.objects.filter(age=999).delete() # clean up first
success = _process_row({ 'Age': 999, 'Gender': 'M', 'Longitude': 31.05, 'Latitude': -17.82, 'Disease_Type': 'Cholera', 'Variant': 'O1 Inaba', 'Date_of_Onset': '2025-01-01' })

case = CholeraCase.objects.filter(age=999).first()
if case:
    print(f"SUCCESS: Age: {case.age}, Gender: {case.gender}, Variant: {case.variant}, Lon: {case.longitude}, Lat: {case.latitude}, Date: {case.date_of_onset}")
else:
    print("FAILED: Case not created.")
