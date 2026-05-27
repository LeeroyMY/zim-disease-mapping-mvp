import json
import os
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from surveillance.models import AdministrativeBoundary

class Command(BaseCommand):
    help = 'Loads Zimbabwe Province Polygons from a GeoJSON file'

    def handle(self, *args, **options):
        file_path = os.path.join('surveillance', 'data', 'zimbabwe_provinces.geojson')
        
        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f"Could not find the file at {file_path}! Please ensure it is in the correct folder."))
            return

        # --- NEW: Delete the old "Unknown Provinces" so we don't get duplicates ---
        self.stdout.write('Clearing old province data...')
        AdministrativeBoundary.objects.filter(level='province').delete()

        self.stdout.write('Reading Province GeoJSON data...')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        provinces_created = 0
        for feature in data['features']:
            props = feature['properties']
            
            # --- UPDATED: Look specifically for 'adm1_name' ---
            name = props.get('adm1_name') or props.get('ADM1_EN') or props.get('NAME_1') or props.get('name') or 'Unknown Province'
            
            # Look for lowercase p-code variations as well
            code = props.get('adm1_pcode') or props.get('ADM1_PCODE') or props.get('ID_1') or props.get('id') or str(provinces_created)
            
            # Convert the text coordinates into PostGIS math
            geom_str = json.dumps(feature['geometry'])
            geom = GEOSGeometry(geom_str)

            # Django models require a MultiPolygon
            if geom.geom_type == 'Polygon':
                geom = MultiPolygon(geom)

            # Save it to the database
            AdministrativeBoundary.objects.create(
                code=code,
                name=name,
                level='province',
                geom=geom
            )
            provinces_created += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {provinces_created} correctly named Provinces into the database!'))