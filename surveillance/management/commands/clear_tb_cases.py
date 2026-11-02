from django.core.management.base import BaseCommand
from django.core.cache import cache
from surveillance.models import TBCase, GenericDiseaseCase

class Command(BaseCommand):
    help = 'Deletes all Tuberculosis (TB) cases from the database and clears the cache.'

    def handle(self, *args, **options):
        tb_count = TBCase.objects.count()
        TBCase.objects.all().delete()
        
        gen_count = GenericDiseaseCase.objects.filter(disease_type__in=['tb', 'tuberculosis']).count()
        GenericDiseaseCase.objects.filter(disease_type__in=['tb', 'tuberculosis']).delete()
        
        cache.delete('all_cases_geojson')
        total = tb_count + gen_count
        self.stdout.write(self.style.SUCCESS(f'Successfully cleared {total} TB cases from the database.'))

