import os
import django
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from surveillance.models import CholeraCase, HIVCase, TBCase

print('Cholera:', CholeraCase.objects.count())
print('Cholera w/ clinic/hospital:', CholeraCase.objects.filter(facility__name__icontains='clinic').count() + CholeraCase.objects.filter(facility__name__icontains='hospital').count())
print('HIV:', HIVCase.objects.count())
print('HIV w/ clinic/hospital:', HIVCase.objects.filter(facility__name__icontains='clinic').count() + HIVCase.objects.filter(facility__name__icontains='hospital').count())
print('TB:', TBCase.objects.count())
print('TB w/ clinic/hospital:', TBCase.objects.filter(facility__name__icontains='clinic').count() + TBCase.objects.filter(facility__name__icontains='hospital').count())

print('Sample Cholera variants:', list(CholeraCase.objects.values_list('variant', flat=True)[:10]))
