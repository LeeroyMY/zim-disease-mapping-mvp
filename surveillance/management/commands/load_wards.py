import json
import os
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from surveillance.models import AdministrativeBoundary

class Command(BaseCommand):
    help = 'Loads Zimbabwe Ward Polygons from a GeoJSON file'

    def handle(self, *args, **options):
        # Pointing to the wards file in your data folder
        file_path = os.path.join('surveillance', 'data', 'zimbabwe_wards.geojson')
        
        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f"Could not find the file at {file_path}! Please ensure it is in the correct folder."))
            return

        self.stdout.write('Clearing old ward data to prevent duplicates...')
        AdministrativeBoundary.objects.filter(level='ward').delete()

        self.stdout.write('Reading Ward GeoJSON data... (This might take a moment, Zimbabwe has ~1,900+ wards)')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        wards_created = 0
        for feature in data['features']:
            props = feature['properties']
            
            # --- STRICTLY USING 'adm3_name' AS REQUESTED ---
            name = props.get('adm3_name') or props.get('ADM3_EN') or props.get('NAME_3') or 'Unknown Ward'
            
            # Grabbing the ward P-code (or generating a unique fallback if missing)
            code = props.get('adm3_pcode') or props.get('ADM3_PCODE') or props.get('ID_3') or f"WARD_{wards_created}"
            
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
                level='ward', #Tagged strictly as a Ward
                geom=geom
            )
            wards_created += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {wards_created} Wards into the database!'))