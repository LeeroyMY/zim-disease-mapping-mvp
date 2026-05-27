import os
os.environ['PATH'] = r"C:\Users\user\AppData\Local\Programs\OSGeo4W\bin;" + os.environ.get('PATH', '')
os.environ['PROJ_LIB'] = r'C:\Users\user\AppData\Local\Programs\OSGeo4W\share\proj'
os.environ['GDAL_DATA'] = r'C:\Users\user\AppData\Local\Programs\OSGeo4W\share\gdal'

import django
import json
import pandas as pd
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from surveillance.models import BaseDiseaseCase, CholeraCase, TBCase, HIVCase
# Clear cases for clean test
for model in [CholeraCase, TBCase, HIVCase]:
    model.objects.all().delete()

from surveillance.views import _process_row

def test_csv():
    print("Testing CSV-like row...")
    row = {
        'disease_type': 'cholera',
        'variant': 'O1 Inaba',
        'age': '22',
        'gender': 'M',
        'date_of_onset': '2026-03-01',
        'location_name': 'Test Village',
        'lat': '-19.0',
        'lon': '29.0'
    }
    _process_row(row, CholeraCase)

def test_excel():
    print("Testing Excel-like row (pandas nan/blank)...")
    row = {
        'disease_type': 'tb',
        'variant': 'MDR-TB',
        'age': '', # pandas might give blank or nan
        'gender': 'F',
        'date_of_onset': '2026-03-02 00:00:00', # Pandas timestamp string
        'location_name': 'Test City',
        'lat': -20.0,
        'lon': 30.0
    }
    _process_row(row, TBCase)

def test_geojson():
    print("Testing GeoJSON-like row...")
    props = {
        'disease_type': 'hiv',
        'variant': 'HIV-1',
        'age': 45,
        'gender': 'M',
        'date_of_onset': '2026-03-03',
        'location_name': 'Geo Town',
        'lat': -18.0,
        'lon': 31.0
    }
    _process_row(props, HIVCase)

def test_nwk():
    print("Testing NWK/Tree-like node extraction...")
    node_name = "Patient_A_StrainX"
    row = {
        'disease_type': 'unknown',
        'variant': node_name,
        'lon': 0,
        'lat': 0
    }
    _process_row(row, CholeraCase)

if __name__ == '__main__':
    test_csv()
    test_excel()
    test_geojson()
    test_nwk()

    print("\n--- Rows in Database ---")
    for model in [CholeraCase, TBCase, HIVCase]:
        for c in model.objects.all():
            print(f"[{c.disease_type}] {c.variant} | Age: {c.age} | Loc: {c.location.y}, {c.location.x} | Facility: {c.facility}")

