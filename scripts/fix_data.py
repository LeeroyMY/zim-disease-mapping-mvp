import os
import django

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from surveillance.models import CholeraCase, HIVCase, TBCase

print("Starting data migration...")

tb_in_cholera = list(CholeraCase.objects.filter(variant__icontains='tb')) + list(CholeraCase.objects.filter(disease_type__icontains='tb'))
tb_set = set(tb_in_cholera)
print(f"Moving {len(tb_set)} TB cases out of CholeraCase...")
for c in tb_set:
    kwargs = {}
    for f in CholeraCase._meta.fields:
        if f.name != 'id':
            kwargs[f.name] = getattr(c, f.name)
    kwargs['disease_type'] = 'tb'
    kwargs['category'] = 'respiratory'
    TBCase.objects.create(**kwargs)
    c.delete()

hiv_in_cholera = list(CholeraCase.objects.filter(variant__icontains='hiv')) + list(CholeraCase.objects.filter(disease_type__icontains='hiv'))
hiv_set = set(hiv_in_cholera)
print(f"Moving {len(hiv_set)} HIV cases out of CholeraCase...")
for c in hiv_set:
    kwargs = {}
    for f in CholeraCase._meta.fields:
        if f.name != 'id':
            kwargs[f.name] = getattr(c, f.name)
    kwargs['disease_type'] = 'hiv'
    kwargs['category'] = 'other'
    HIVCase.objects.create(**kwargs)
    c.delete()

print(f"Final Counts -> Cholera: {CholeraCase.objects.count()}, TB: {TBCase.objects.count()}, HIV: {HIVCase.objects.count()}")
