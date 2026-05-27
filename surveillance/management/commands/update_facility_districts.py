from django.core.management.base import BaseCommand
from surveillance.models import HealthFacility, AdministrativeBoundary

class Command(BaseCommand):
    help = 'Performs a Spatial Join to assign Districts to Health Facilities based on GPS'

    def handle(self, *args, **kwargs):
        # 1. Find all facilities that currently say "Unknown"
        facilities = HealthFacility.objects.filter(district_name='Unknown')
        
        self.stdout.write(f'Found {facilities.count()} facilities with Unknown districts. Starting spatial join...')
        
        updated_count = 0
        
        for facility in facilities:
            # 2. THE MAGIC LINE: Find the District Polygon that "contains" the Facility Point
            # Django automatically translates 'geom__contains' into an advanced PostGIS spatial query!
            matching_district = AdministrativeBoundary.objects.filter(geom__contains=facility.location).first()
            
            if matching_district:
                # 3. Update the facility with the mathematically proven district name
                facility.district_name = matching_district.name
                facility.save()
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'Success! {updated_count} facilities mathematically assigned to their correct districts!'))