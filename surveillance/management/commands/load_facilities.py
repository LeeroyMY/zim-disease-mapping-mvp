import json
import os
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from surveillance.models import HealthFacility

class Command(BaseCommand):
    help = 'Loads Real Zimbabwe Health Facilities from GeoJSON'

    def handle(self, *args, **kwargs):
        file_path = os.path.join('surveillance', 'data', 'zim_health_facilities.geojson')

        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        self.stdout.write('Opening GeoJSON file...')
        with open(file_path, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)

        self.stdout.write('Clearing old facility data...')
        HealthFacility.objects.all().delete()

        self.stdout.write('Importing real health facilities. Please wait...')
        
        count = 0
        for feature in geojson_data['features']:
            # Make sure it's a Point geometry
            if feature['geometry'] is None or feature['geometry']['type'] != 'Point':
                continue

            props = feature.get('properties', {})
            
            # Extract the Name
            name = props.get('name')
            
            # If the facility doesn't have a name, skip it
            if not name:
                continue

            # Extract District (using the exact column from your diagnostics)
            district = props.get('addr_city') or 'Unknown'
            
            # The HDX file doesn't have a province column, so we default to Unknown
            province = 'Unknown'

            # Extract Coordinates
            coords = feature['geometry'].get('coordinates')
            if not coords or len(coords) < 2:
                continue

            location = Point(coords[0], coords[1], srid=4326)

            # Save to Database
            HealthFacility.objects.create(
                name=name,
                district_name=district,
                province=province,
                location=location
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {count} real health facilities!'))