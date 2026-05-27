import re

with open(r'c:\Users\user\infectious_diseases_mapping\surveillance\views.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_process = '''def _process_row(row):
    def get_alias(keys, default=''):
        for k in keys:
            if k in row and row[k] not in [None, '', 'nan']:
                return row[k]
        return default

    try:
        dt_str = str(get_alias(['date_of_onset', 'date', 'onset_date'])).strip()
        parsed_date = None
        if dt_str and dt_str != 'nan':
            try:
                if isinstance(dt_str, str) and len(dt_str) >= 10:
                    parsed_date = datetime.strptime(dt_str[:10], '%Y-%m-%d').date()
            except:
                pass
                
        lon_val = get_alias(['lon', 'longitude', 'longtude', 'lng '])
        lat_val = get_alias(['lat', 'latitude'])
        lon = float(lon_val) if lon_val not in ['', None, 'nan'] else 0.0
        lat = float(lat_val) if lat_val not in ['', None, 'nan'] else 0.0
        
        age_val = get_alias(['age', 'patient_age'])
        age = int(float(age_val)) if age_val not in ['', None, 'nan'] else None
        
        disease_type = str(get_alias(['disease_type', 'disease', 'condition'], 'unknown')).lower()
        if disease_type not in ['cholera', 'tb', 'hiv']:
            disease_type = 'cholera'
            
        DiseaseCase.objects.create(
            disease_type=disease_type,
            variant=str(get_alias(['variant', 'strain', 'type'])),
            age=age,
            gender=str(get_alias(['gender', 'sex', 'patient_gender'], 'U'))[:1].upper(),
            date_of_onset=parsed_date,
            location_name=str(get_alias(['location_name', 'location', 'city', 'district', 'region'])),
            location=Point(lon, lat, srid=4326),
            severity=3,
            outcome='active'
        )
        return True
    except Exception as e:
        return False
'''

# Find def _process_row(row): ... return False
pattern = re.compile(r'def _process_row\(row\):.*?return False', re.DOTALL)
new_content = pattern.sub(new_process, content)

with open(r'c:\Users\user\infectious_diseases_mapping\surveillance\views.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Updated views.py successfully")
