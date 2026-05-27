import random
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.db import models
from surveillance.models import CholeraCase, HIVCase, TBCase, MalariaCase, TyphoidCase, HealthFacility

class Command(BaseCommand):
    help = 'Generates dynamic cases with epidemiological realism, demographics, and capable spatial routing'

    def add_arguments(self, parser):
        parser.add_argument('total', type=int, nargs='?', default=10000, help='Total number of cases to generate')

    def handle(self, *args, **options):
        target_total = options['total']
        
        # 90% background noise across the country, 10% concentrated hotspots
        background_target = int(target_total * 0.9)
        hotspot_target = target_total - background_target

        # Background splits
        hiv_tb_target = int(background_target * (8500 / 9000.0))
        noise_target = background_target - hiv_tb_target

        # Hotspot splits
        malaria_hotspot_target = int(hotspot_target * 0.45)
        cholera_hotspot_target = int(hotspot_target * 0.35)
        typhoid_hotspot_target = hotspot_target - malaria_hotspot_target - cholera_hotspot_target

        if not HealthFacility.objects.exists():
            self.stderr.write(self.style.ERROR("No facilities found! Please run your load_facilities command first."))
            return

        self.stdout.write(f'Deleting old mock data and preparing to generate exactly {target_total} cases...')
        CholeraCase.objects.all().delete()
        HIVCase.objects.all().delete()
        TBCase.objects.all().delete()
        MalariaCase.objects.all().delete()
        TyphoidCase.objects.all().delete() 

        # Universally exclude pharmacy and maternity for all infectious diseases
        capable_facilities = HealthFacility.objects.filter(
            models.Q(name__icontains='clinic') | 
            models.Q(name__icontains='hospital')
        ).exclude(
            models.Q(name__icontains='pharmacy') | 
            models.Q(name__icontains='maternity')
        )

        if not capable_facilities.exists():
            self.stderr.write(self.style.ERROR("No capable facilities left after filtering!"))
            return

        # --- MASSIVE DICTIONARY OF REAL ZIMBABWEAN LOCATIONS ---
        REAL_LOCATIONS = [
            # HARARE (Urban)
            {"name": "Mt Pleasant, Harare", "lon": 31.0425, "lat": -17.7664, "type": "urban", "malaria_endemic": False},
            {"name": "Mbare, Harare", "lon": 31.0400, "lat": -17.8550, "type": "urban", "malaria_endemic": False},
            {"name": "Highfield, Harare", "lon": 30.9880, "lat": -17.8820, "type": "urban", "malaria_endemic": False},
            {"name": "Mabvuku, Harare", "lon": 31.1850, "lat": -17.8380, "type": "urban", "malaria_endemic": False},
            {"name": "Tafara, Harare", "lon": 31.2050, "lat": -17.8300, "type": "urban", "malaria_endemic": False},
            {"name": "Kuwadzana, Harare", "lon": 30.9300, "lat": -17.8300, "type": "urban", "malaria_endemic": False},
            {"name": "Dzivarasekwa, Harare", "lon": 30.9500, "lat": -17.7900, "type": "urban", "malaria_endemic": False},
            {"name": "Warren Park, Harare", "lon": 30.9800, "lat": -17.8250, "type": "urban", "malaria_endemic": False},
            {"name": "Borrowdale, Harare", "lon": 31.0900, "lat": -17.7600, "type": "urban", "malaria_endemic": False},
            {"name": "Budiriro, Harare", "lon": 30.9300, "lat": -17.8800, "type": "urban", "malaria_endemic": False},
            {"name": "Glen View, Harare", "lon": 30.9300, "lat": -17.8900, "type": "urban", "malaria_endemic": False},
            {"name": "Glen Norah, Harare", "lon": 30.9600, "lat": -17.8950, "type": "urban", "malaria_endemic": False},
            {"name": "Waterfalls, Harare", "lon": 31.0300, "lat": -17.9100, "type": "urban", "malaria_endemic": False},
            {"name": "Hatfield, Harare", "lon": 31.0800, "lat": -17.8800, "type": "urban", "malaria_endemic": False},
            {"name": "Highlands, Harare", "lon": 31.1000, "lat": -17.7900, "type": "urban", "malaria_endemic": False},
            {"name": "Greendale, Harare", "lon": 31.1300, "lat": -17.8000, "type": "urban", "malaria_endemic": False},
            {"name": "Mabelreign, Harare", "lon": 30.9900, "lat": -17.7800, "type": "urban", "malaria_endemic": False},
            {"name": "Marlborough, Harare", "lon": 30.9900, "lat": -17.7500, "type": "urban", "malaria_endemic": False},
            {"name": "Avondale, Harare", "lon": 31.0300, "lat": -17.7900, "type": "urban", "malaria_endemic": False},
            {"name": "Belvedere, Harare", "lon": 31.0200, "lat": -17.8200, "type": "urban", "malaria_endemic": False},

            # CHITUNGWIZA (Urban)
            {"name": "Zengeza, Chitungwiza", "lon": 31.0500, "lat": -18.0000, "type": "urban", "malaria_endemic": False},
            {"name": "Seke, Chitungwiza", "lon": 31.0700, "lat": -18.0200, "type": "urban", "malaria_endemic": False},
            {"name": "St Marys, Chitungwiza", "lon": 31.0300, "lat": -17.9800, "type": "urban", "malaria_endemic": False},

            # BULAWAYO (Urban)
            {"name": "Makokoba, Bulawayo", "lon": 28.5714, "lat": -20.1517, "type": "urban", "malaria_endemic": False},
            {"name": "Nkulumane, Bulawayo", "lon": 28.5130, "lat": -20.2110, "type": "urban", "malaria_endemic": False},
            {"name": "Pumula, Bulawayo", "lon": 28.4800, "lat": -20.1500, "type": "urban", "malaria_endemic": False},
            {"name": "Cowdray Park, Bulawayo", "lon": 28.4800, "lat": -20.0800, "type": "urban", "malaria_endemic": False},
            {"name": "Emakhandeni, Bulawayo", "lon": 28.5300, "lat": -20.1100, "type": "urban", "malaria_endemic": False},
            {"name": "Entumbane, Bulawayo", "lon": 28.5400, "lat": -20.1200, "type": "urban", "malaria_endemic": False},
            {"name": "Lobengula, Bulawayo", "lon": 28.5100, "lat": -20.1400, "type": "urban", "malaria_endemic": False},
            {"name": "Luveve, Bulawayo", "lon": 28.5100, "lat": -20.1100, "type": "urban", "malaria_endemic": False},
            {"name": "Magwegwe, Bulawayo", "lon": 28.4900, "lat": -20.1300, "type": "urban", "malaria_endemic": False},
            {"name": "Mpopoma, Bulawayo", "lon": 28.5400, "lat": -20.1500, "type": "urban", "malaria_endemic": False},
            {"name": "Sizinda, Bulawayo", "lon": 28.5600, "lat": -20.1800, "type": "urban", "malaria_endemic": False},
            {"name": "Tshabalala, Bulawayo", "lon": 28.5500, "lat": -20.1900, "type": "urban", "malaria_endemic": False},
            {"name": "Hillside, Bulawayo", "lon": 28.6000, "lat": -20.1900, "type": "urban", "malaria_endemic": False},
            {"name": "Burnside, Bulawayo", "lon": 28.6200, "lat": -20.2100, "type": "urban", "malaria_endemic": False},
            {"name": "Famona, Bulawayo", "lon": 28.5800, "lat": -20.1800, "type": "urban", "malaria_endemic": False},
            {"name": "Bradfield, Bulawayo", "lon": 28.5900, "lat": -20.1700, "type": "urban", "malaria_endemic": False},
            {"name": "Sauerstown, Bulawayo", "lon": 28.5900, "lat": -20.1300, "type": "urban", "malaria_endemic": False},
            {"name": "Queens Park, Bulawayo", "lon": 28.6100, "lat": -20.1400, "type": "urban", "malaria_endemic": False},
            {"name": "Waterford, Bulawayo", "lon": 28.6300, "lat": -20.1900, "type": "urban", "malaria_endemic": False},
            {"name": "Matsheumhlope, Bulawayo", "lon": 28.6300, "lat": -20.1700, "type": "urban", "malaria_endemic": False},

            # MUTARE (Urban)
            {"name": "Dangamvura, Mutare", "lon": 32.6100, "lat": -18.9950, "type": "urban", "malaria_endemic": False},
            {"name": "Sakubva, Mutare", "lon": 32.6240, "lat": -18.9850, "type": "urban", "malaria_endemic": False},
            {"name": "Chikanga, Mutare", "lon": 32.6100, "lat": -18.9500, "type": "urban", "malaria_endemic": False},
            {"name": "Hobhouse, Mutare", "lon": 32.6100, "lat": -18.9800, "type": "urban", "malaria_endemic": False},
            {"name": "Morningside, Mutare", "lon": 32.6400, "lat": -18.9900, "type": "urban", "malaria_endemic": False},
            {"name": "Palmerston, Mutare", "lon": 32.6500, "lat": -18.9600, "type": "urban", "malaria_endemic": False},
            {"name": "Murambi, Mutare", "lon": 32.6600, "lat": -18.9600, "type": "urban", "malaria_endemic": False},
            {"name": "Florida, Mutare", "lon": 32.6500, "lat": -18.9800, "type": "urban", "malaria_endemic": False},
            {"name": "Yeovil, Mutare", "lon": 32.6300, "lat": -18.9700, "type": "urban", "malaria_endemic": False},
            {"name": "Fern Valley, Mutare", "lon": 32.6500, "lat": -19.0300, "type": "urban", "malaria_endemic": False},

            # GWERU (Urban)
            {"name": "Mkoba, Gweru", "lon": 29.7750, "lat": -19.4640, "type": "urban", "malaria_endemic": False},
            {"name": "Ascot, Gweru", "lon": 29.8300, "lat": -19.4600, "type": "urban", "malaria_endemic": False},
            {"name": "Mtapa, Gweru", "lon": 29.8100, "lat": -19.4500, "type": "urban", "malaria_endemic": False},
            {"name": "Senga, Gweru", "lon": 29.8300, "lat": -19.4900, "type": "urban", "malaria_endemic": False},
            {"name": "Southdowns, Gweru", "lon": 29.8100, "lat": -19.4800, "type": "urban", "malaria_endemic": False},
            {"name": "Windsor Park, Gweru", "lon": 29.8400, "lat": -19.4600, "type": "urban", "malaria_endemic": False},
            {"name": "Lundi Park, Gweru", "lon": 29.8200, "lat": -19.4700, "type": "urban", "malaria_endemic": False},
            {"name": "Daylesford, Gweru", "lon": 29.8500, "lat": -19.5000, "type": "urban", "malaria_endemic": False},

            # MASVINGO (Urban)
            {"name": "Mucheke, Masvingo", "lon": 30.8200, "lat": -20.0800, "type": "urban", "malaria_endemic": False},
            {"name": "Rujeko, Masvingo", "lon": 30.8500, "lat": -20.0900, "type": "urban", "malaria_endemic": False},
            {"name": "Rhodene, Masvingo", "lon": 30.8300, "lat": -20.0600, "type": "urban", "malaria_endemic": False},
            {"name": "Target Kopje, Masvingo", "lon": 30.8100, "lat": -20.0900, "type": "urban", "malaria_endemic": False},
            {"name": "Victoria Range, Masvingo", "lon": 30.8000, "lat": -20.0800, "type": "urban", "malaria_endemic": False},

            # RURAL GROWTH POINTS & DISTRICT CENTERS
            {"name": "Murewa Growth Point, Mash East", "lon": 31.7833, "lat": -17.6500, "type": "rural", "malaria_endemic": False},
            {"name": "Mutoko Center, Mash East", "lon": 32.2200, "lat": -17.4000, "type": "rural", "malaria_endemic": True},
            {"name": "Mpandawana (Gutu), Masvingo", "lon": 31.1681, "lat": -19.6436, "type": "rural", "malaria_endemic": False},
            {"name": "Jerera Growth Point (Zaka), Masvingo", "lon": 31.4500, "lat": -20.3300, "type": "rural", "malaria_endemic": False},
            {"name": "Murambinda, Mash West", "lon": 31.6600, "lat": -19.2600, "type": "rural", "malaria_endemic": False},
            {"name": "Gokwe Center, Midlands", "lon": 28.9350, "lat": -18.2180, "type": "rural", "malaria_endemic": True},
            {"name": "Nkayi Center, Mat North", "lon": 28.9000, "lat": -19.0000, "type": "rural", "malaria_endemic": True},
            {"name": "Tsholotsho Center, Mat North", "lon": 27.7630, "lat": -19.7650, "type": "rural", "malaria_endemic": True},
            {"name": "Plumtree Town, Mat South", "lon": 27.8000, "lat": -20.4800, "type": "rural", "malaria_endemic": False},
            {"name": "Karoi Center, Mash West", "lon": 29.6900, "lat": -16.8100, "type": "rural", "malaria_endemic": True},
            {"name": "Sanyati Growth Point, Mash West", "lon": 29.3000, "lat": -17.3000, "type": "rural", "malaria_endemic": True},
            {"name": "Chivi Growth Point, Masvingo", "lon": 30.5000, "lat": -20.3000, "type": "rural", "malaria_endemic": False},
            {"name": "Rutenga (Mwenezi), Masvingo", "lon": 30.7300, "lat": -21.1800, "type": "rural", "malaria_endemic": True},
            {"name": "Binga Center, Mat North", "lon": 27.3400, "lat": -17.6200, "type": "rural", "malaria_endemic": True},
            {"name": "Lupane Center, Mat North", "lon": 27.8000, "lat": -18.9300, "type": "rural", "malaria_endemic": True},
            {"name": "Muzarabani Center, Mash Central", "lon": 31.0000, "lat": -16.4000, "type": "rural", "malaria_endemic": True},

            # FAMOUS MISSION SETTLEMENTS
            {"name": "Howard Mission, Chiweshe", "lon": 30.9300, "lat": -17.2300, "type": "rural", "malaria_endemic": False},
            {"name": "Mt Selinda Mission, Chipinge", "lon": 32.7000, "lat": -20.4000, "type": "rural", "malaria_endemic": True},
            {"name": "Nyadire Mission, Mutoko", "lon": 32.1100, "lat": -17.1500, "type": "rural", "malaria_endemic": True},
            {"name": "Mutambara Mission, Chimanimani", "lon": 32.7300, "lat": -19.1900, "type": "rural", "malaria_endemic": True},
            {"name": "St Luke's Mission, Lupane", "lon": 27.7300, "lat": -18.9600, "type": "rural", "malaria_endemic": True},
            {"name": "Mnene Mission, Mberengwa", "lon": 29.9800, "lat": -20.8300, "type": "rural", "malaria_endemic": False},
            {"name": "Silveira Mission, Bikita", "lon": 31.6800, "lat": -20.0500, "type": "rural", "malaria_endemic": False}
        ]

        severity_choices = [c[0] for c in CholeraCase._meta.get_field('severity').choices]
        outcome_choices = [c[0] for c in CholeraCase._meta.get_field('outcome').choices]

        cholera_cases_to_create = []
        tb_cases_to_create = []
        hiv_cases_to_create = []
        malaria_cases_to_create = []
        typhoid_cases_to_create = []

        # ==========================================
        # HELPER FOR CREATING A CASE
        # ==========================================
        def create_case(disease, epicenter, is_hotspot=False, mock_days_ago=None):
            scatter_factor = 0.005 if is_hotspot else (0.03 if epicenter.get("type") == "rural" else 0.015)
            house_lon = epicenter["lon"] + random.uniform(-scatter_factor, scatter_factor)
            house_lat = epicenter["lat"] + random.uniform(-scatter_factor, scatter_factor)
            
            location_point = Point(house_lon, house_lat, srid=4326)

            closest_facilities = capable_facilities.annotate(
                distance=Distance('location', location_point)
            ).order_by('distance')[:5]

            assigned_facility = random.choice(closest_facilities) if closest_facilities.exists() else None

            # Demographics and Temporal Logic
            variant = None
            if disease in ['hiv', 'tb']:
                age = int(random.triangular(15, 85, 30))
                days_ago = random.randint(100, 3000) if mock_days_ago is None else mock_days_ago
                if disease == 'hiv':
                    gender = random.choices(['F', 'M'], weights=[0.60, 0.40])[0]
                    variant = random.choices(['HIV-1', 'HIV-2'], weights=[0.9, 0.1])[0]
                else:
                    gender = random.choice(['M', 'F'])
                    variant = random.choices(['MDR-TB', 'XDR-TB', None], weights=[0.15, 0.05, 0.8])[0]
            else:
                age = int(random.betavariate(2, 5) * 80)
                days_ago = random.randint(5, 60) if mock_days_ago is None else mock_days_ago
                gender = random.choice(['M', 'F'])
                if disease == 'cholera':
                    variant = random.choices(['O1 Ogawa', 'O1 Inaba', None], weights=[0.6, 0.2, 0.2])[0]
                elif disease == 'malaria':
                    variant = random.choices(['P. falciparum', 'P. vivax', None], weights=[0.8, 0.1, 0.1])[0]
                elif disease == 'typhoid':
                    variant = random.choices(['S. Typhi', 'S. Paratyphi', None], weights=[0.8, 0.1, 0.1])[0]

            mock_date = timezone.now().date() - timedelta(days=days_ago)

            if disease == 'cholera':
                ModelClass, lst = CholeraCase, cholera_cases_to_create
            elif disease == 'tb':
                ModelClass, lst = TBCase, tb_cases_to_create
            elif disease == 'hiv':
                ModelClass, lst = HIVCase, hiv_cases_to_create
            elif disease == 'malaria':
                ModelClass, lst = MalariaCase, malaria_cases_to_create
            elif disease == 'typhoid':
                ModelClass, lst = TyphoidCase, typhoid_cases_to_create
            
            case = ModelClass(
                disease_type=disease,
                variant=variant,
                age=age,
                gender=gender,
                severity=random.choice(severity_choices),
                outcome=random.choice(outcome_choices),
                date_of_onset=mock_date,
                location=location_point,
                longitude=house_lon,
                latitude=house_lat,
                facility=assigned_facility,      
                location_name=epicenter["name"]  
            )
            lst.append(case)

        # ==========================================
        # 1. GENERATE HIV & TB BACKGROUND
        # ==========================================
        self.stdout.write(f'Generating {hiv_tb_target} HIV & TB background cases...')
        for i in range(hiv_tb_target):
            home_area = random.choice(REAL_LOCATIONS)
            disease = random.choices(['hiv', 'tb'], weights=[0.65, 0.35])[0]
            create_case(disease, home_area)

        # ==========================================
        # 2. GENERATE LOW-LEVEL ENDEMIC NOISE
        # ==========================================
        self.stdout.write(f'Generating {noise_target} low-level endemic noise cases (Typhoid & Malaria)...')
        urban_locations = [l for l in REAL_LOCATIONS if l["type"] == "urban"]
        malaria_locations = [l for l in REAL_LOCATIONS if l.get("malaria_endemic")]
        
        for i in range(noise_target):
            # 50/50 split between Typhoid and Malaria for noise
            disease = random.choice(['typhoid', 'malaria'])
            if disease == 'typhoid':
                create_case(disease, random.choice(urban_locations))
            else:
                create_case(disease, random.choice(malaria_locations))

        # ==========================================
        # 3. GENERATE HOTSPOTS
        # ==========================================
        self.stdout.write(self.style.WARNING(f'Generating {hotspot_target} structured localized hotspots...'))

        # A) Malaria Flare-up in Binga & Muzarabani (45% of hotspots)
        self.stdout.write(f'  -> {malaria_hotspot_target} Malaria cases in Binga/Muzarabani')
        malaria_hotspot_locs = [l for l in REAL_LOCATIONS if "Binga" in l["name"] or "Muzarabani" in l["name"]]
        for _ in range(malaria_hotspot_target):
            days_ago = int(random.triangular(5, 60, 30))
            create_case('malaria', random.choice(malaria_hotspot_locs), is_hotspot=True, mock_days_ago=days_ago)

        # B) Cholera Flare-up in WASH Corridor (35% of hotspots)
        self.stdout.write(f'  -> {cholera_hotspot_target} Cholera cases in WASH Corridor')
        cholera_hotspot_locs = [l for l in REAL_LOCATIONS if "Kuwadzana" in l["name"] or "Glen View" in l["name"] or "Budiriro" in l["name"]]
        for _ in range(cholera_hotspot_target):
            days_ago = int(random.triangular(5, 45, 15))
            create_case('cholera', random.choice(cholera_hotspot_locs), is_hotspot=True, mock_days_ago=days_ago)

        # C) Typhoid Flare-up in Mbare & Zengeza (20% of hotspots)
        self.stdout.write(f'  -> {typhoid_hotspot_target} Typhoid cases in Mbare/Zengeza')
        typhoid_hotspot_locs = [l for l in REAL_LOCATIONS if "Mbare" in l["name"] or "Zengeza" in l["name"]]
        for _ in range(typhoid_hotspot_target):
            days_ago = int(random.triangular(10, 60, 35))
            create_case('typhoid', random.choice(typhoid_hotspot_locs), is_hotspot=True, mock_days_ago=days_ago)

        # ==========================================
        # 4. BULK CREATE TO DATABASE
        # ==========================================
        self.stdout.write('Writing all cases to the database. This will only take a moment...')
        if cholera_cases_to_create: CholeraCase.objects.bulk_create(cholera_cases_to_create, batch_size=1000)
        if tb_cases_to_create: TBCase.objects.bulk_create(tb_cases_to_create, batch_size=1000)
        if hiv_cases_to_create: HIVCase.objects.bulk_create(hiv_cases_to_create, batch_size=1000)
        if malaria_cases_to_create: MalariaCase.objects.bulk_create(malaria_cases_to_create, batch_size=1000)
        if typhoid_cases_to_create: TyphoidCase.objects.bulk_create(typhoid_cases_to_create, batch_size=1000)

        self.stdout.write(self.style.SUCCESS(f'Successfully generated exactly {target_total} total cases logically mapped and optimized!'))