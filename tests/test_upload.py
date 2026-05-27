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

# create a test user if not exists
user, _ = User.objects.get_or_create(username='testuser')
user.set_password('password')
user.save()

client = Client()
client.force_login(user)

csv_content = b"lat,lon,date_of_onset,facility,disease_type,variant\n-19.0,29.0,2026-03-01,Test Clinic,cholera,O1 Inaba"

file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")

response = client.post('/api/upload/', {
    'file': file,
    'disease_type': 'cholera'
})

print(response.status_code)
print(response.json())

from surveillance.models import CholeraCase
print("Cholera cases count:", CholeraCase.objects.count())
