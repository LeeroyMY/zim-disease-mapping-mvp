import os
os.environ['PATH'] = r"C:\Users\user\AppData\Local\Programs\OSGeo4W\bin;" + os.environ.get('PATH', '')
os.environ['PROJ_LIB'] = r'C:\Users\user\AppData\Local\Programs\OSGeo4W\share\proj'
os.environ['GDAL_DATA'] = r'C:\Users\user\AppData\Local\Programs\OSGeo4W\share\gdal'

import django
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from surveillance.models import GenericDiseaseCase

user, _ = User.objects.get_or_create(username='testuser')
user.set_password('password')
user.save()

client = Client()
client.force_login(user)

csv_content = b"lat,lon,date_of_onset,facility,disease_type,variant,custom_symptom,blood_pressure\n-19.0,29.0,2026-03-01,Test Clinic,malaria,falciparum,fever,120/80"

file = SimpleUploadedFile("test_malaria.csv", csv_content, content_type="text/csv")

response = client.post('/api/upload/', {
    'file': file,
    'disease_type': 'malaria'
})

print("Upload Response:", response.status_code)
print(response.json())

cases = GenericDiseaseCase.objects.filter(disease_type='malaria')
print("Malaria cases count:", cases.count())
if cases.exists():
    print("Extra Data for first case:", cases.first().extra_data)
