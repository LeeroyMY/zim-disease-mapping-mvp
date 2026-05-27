import os
import django
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.test import RequestFactory
from surveillance.views import get_disease_data, get_all_cases
import json

rf = RequestFactory()

for d in ['cholera', 'hiv', 'tb']:
    request = rf.get(f'/api/table-cases/{d}/')
    response = get_disease_data(request, d)
    data = json.loads(response.content)
    print(f'Disease: {d}, Count in table API: {len(data.get("data", []))}')

request = rf.get('/api/cases/')
response = get_all_cases(request)
data = json.loads(response.content)
print('Total across all cases API:', len(data.get('features', [])))
