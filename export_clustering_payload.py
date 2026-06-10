import os
import django
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.apps import apps
from surveillance.models import BaseDiseaseCase

def get_all_disease_models():
    models_list = []
    for model in apps.get_models():
        if issubclass(model, BaseDiseaseCase) and model is not BaseDiseaseCase:
            models_list.append(model)
    return models_list

points = []
for model in get_all_disease_models():
    cases = model.objects.all()
    for case in cases:
        if case.longitude and case.latitude and case.longitude != 0.0 and case.latitude != 0.0:
            date_str = None
            if case.date_reported:
                date_str = case.date_reported.strftime('%Y-%m-%d')
            points.append({
                "lon": case.longitude,
                "lat": case.latitude,
                "date": date_str
            })

payload = {
    "diseases": ["mixed"],
    "points": points
}

with open('clustering_payload.json', 'w') as f:
    json.dump(payload, f)

print(f"Exported {len(points)} points to clustering_payload.json")
