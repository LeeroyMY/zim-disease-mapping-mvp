import json
import os
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from surveillance.models import AdministrativeBoundary

class Command(BaseCommand):
    help = 'Loads Real Zimbabwe Administrative Boundaries from GeoJSON'

    def handle(self, *args, **kwargs):
        file_path = os.path.join('surveillance', 'data', 'zimbabwe_districts.geojson')

        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        self.stdout.write('Opening GeoJSON file...')
        with open(file_path, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)

        self.stdout.write('Clearing old boundary data...')
        AdministrativeBoundary.objects.all().delete()

        self.stdout.write('Importing real districts into PostGIS. Please wait...')
        
        count = 0
        for feature in geojson_data['features']:
            props = feature['properties']
            
            # --- THE FIX IS HERE ---
            # We explicitly tell it to use 'adm2_name'
            name = props.get('adm2_name') or 'Unknown District'
            
            # We also look for standard ID fields to act as the code
            code = props.get('adm2_pcode') or props.get('adm2_id') or props.get('id') or f'ZWE-{count}'

            geom_str = json.dumps(feature['geometry'])
            geom = GEOSGeometry(geom_str)

            if isinstance(geom, Polygon):
                geom = MultiPolygon(geom)

            AdministrativeBoundary.objects.create(
                name=name,
                code=code,
                level='district',
                geom=geom
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {count} real administrative boundaries!'))