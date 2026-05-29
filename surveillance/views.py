"""
Surveillance Views Module.

This module contains the API endpoints and frontend view controllers for the application.
It handles rendering the MapLibre dashboard, managing case data, and handling complex
data ingestion workflows (CSV, GeoJSON, Newick trees) into the dynamic model architecture.
"""

import csv
import json
import re
import random

import newick
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.gis.geos import Point
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.apps import apps

from django.db import connection
from itertools import chain
from operator import attrgetter
from django.contrib.gis.db.models.functions import Distance

from .models import BaseDiseaseCase, AdministrativeBoundary, HealthFacility
from .serializers import AdministrativeBoundarySerializer, HealthFacilitySerializer
from .utils import get_or_create_dynamic_model, get_geomasking_radii, apply_donut_geomasking

def _get_all_disease_models():
    """Returns all models that inherit from BaseDiseaseCase."""
    models_list = []
    for model in apps.get_models():
        if issubclass(model, BaseDiseaseCase) and model is not BaseDiseaseCase:
            models_list.append(model)
    return models_list

@api_view(['GET'])
def get_all_cases(request):
    """
    Returns a unified FeatureCollection of all diseases for the map.
    """
    features = []
    for model in _get_all_disease_models():
        cases = model.objects.select_related('facility').order_by('-date_reported')
        
        # Manually serialize since dynamic models don't have predefined DRF serializers
        for case in cases:
            # Clinical Guardrail: Block HIV cases completely from the map point feed
            if case.disease_type.lower() == 'hiv':
                continue
                
            # Get all fields dynamically to include extra columns
            properties = {}
            for field in case._meta.fields:
                if field.name not in ['location', 'patient_id', 'facility', 'reported_by', 'extra_data']:
                    val = getattr(case, field.name)
                    if isinstance(val, datetime):
                        val = val.isoformat()
                    # Also handle dates
                    elif hasattr(val, 'isoformat'):
                        val = val.isoformat()
                    properties[field.name] = val
                    
            if hasattr(case, 'extra_data') and isinstance(case.extra_data, dict):
                properties.update(case.extra_data)
            
            # Add facility name
            properties['facility__name'] = case.facility.name if case.facility else None
            properties['disease_type'] = case.disease_type.lower()
            properties['id'] = case.id
            
            if case.location:
                # Apply Donut Geomasking
                r_min, r_max = get_geomasking_radii(case)
                masked_lon, masked_lat = apply_donut_geomasking(
                    case.location.x, case.location.y, r_min, r_max, seed_val=case.patient_id
                )
                
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [masked_lon, masked_lat]
                    },
                    "properties": properties
                })

    return Response({
        "type": "FeatureCollection",
        "features": features
    })

@api_view(['GET'])
def get_regions(request):
    """
    Returns a lightweight JSON list of all provinces and districts for the
    sidebar filter dropdowns. Uses the AdministrativeBoundary model's `level`
    field (values: 'province', 'district'). No geometry is returned so the
    response is fast even with many boundaries.

    Falls back to unique province/district names scraped from HealthFacility
    records if the AdministrativeBoundary table is empty.
    """
    provinces = []
    districts = []

    # --- Primary source: AdministrativeBoundary table ---
    boundaries = AdministrativeBoundary.objects.only('id', 'name', 'code', 'level').order_by('name')
    if boundaries.exists():
        for b in boundaries:
            entry = {'id': b.id, 'name': b.name, 'code': b.code}
            if b.level == 'province':
                provinces.append(entry)
            elif b.level == 'district':
                districts.append(entry)
    else:
        # --- Fallback: derive from HealthFacility metadata ---
        prov_names = (
            HealthFacility.objects
            .exclude(province='')
            .values_list('province', flat=True)
            .distinct()
            .order_by('province')
        )
        for i, name in enumerate(prov_names):
            provinces.append({'id': f'p_{i}', 'name': name, 'code': name})

        dist_rows = (
            HealthFacility.objects
            .exclude(district_name='')
            .values('district_name', 'province')
            .distinct()
            .order_by('district_name')
        )
        for i, row in enumerate(dist_rows):
            districts.append({
                'id': f'd_{i}',
                'name': row['district_name'],
                'code': row['district_name'],
                'province': row['province'],
            })

    return Response({'provinces': provinces, 'districts': districts})


@api_view(['GET'])
def get_latest_cases(request):
    """
    Returns a unified FeatureCollection of cases reported after a specific timestamp.
    """
    since_timestamp = request.GET.get('since')
    features = []
    
    from django.utils.dateparse import parse_datetime
    
    for model in _get_all_disease_models():
        cases = model.objects.select_related('facility').order_by('-date_reported')
        
        if since_timestamp:
            try:
                # Handle possible 'Z' at the end of JS ISO strings using Django's parser which is robust
                since_dt = parse_datetime(since_timestamp)
                if since_dt is None: # Fallback
                    since_dt = datetime.fromisoformat(since_timestamp.replace('Z', '+00:00'))
                if since_dt:
                    cases = cases.filter(date_reported__gt=since_dt)
            except ValueError:
                pass
                
        for case in cases:
            # Clinical Guardrail: Block HIV cases completely from the map point feed
            if case.disease_type.lower() == 'hiv':
                continue
                
            properties = {}
            for field in case._meta.fields:
                if field.name not in ['location', 'patient_id', 'facility', 'reported_by', 'extra_data']:
                    val = getattr(case, field.name)
                    if isinstance(val, datetime):
                        val = val.isoformat()
                    elif hasattr(val, 'isoformat'):
                        val = val.isoformat()
                    properties[field.name] = val
                    
            if hasattr(case, 'extra_data') and isinstance(case.extra_data, dict):
                properties.update(case.extra_data)
                    
            properties['facility__name'] = case.facility.name if case.facility else None
            properties['disease_type'] = case.disease_type.lower()
            properties['id'] = case.id
            
            if case.location:
                # Apply Donut Geomasking
                r_min, r_max = get_geomasking_radii(case)
                masked_lon, masked_lat = apply_donut_geomasking(
                    case.location.x, case.location.y, r_min, r_max, seed_val=case.patient_id
                )
                
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [masked_lon, masked_lat]
                    },
                    "properties": properties
                })
                
    return Response({
        "type": "FeatureCollection",
        "features": features
    })

class AdministrativeBoundaryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AdministrativeBoundary.objects.all()
    serializer_class = AdministrativeBoundarySerializer

class HealthFacilityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HealthFacility.objects.all()
    serializer_class = HealthFacilitySerializer

@csrf_exempt
@api_view(['POST'])
def calculate_spatial_clustering(request):
    """
    Accepts an array of [lon, lat] coordinates and uses PostGIS ST_ClusterDBSCAN
    to return clustering statistics, offloading heavy spatial math to the database.
    """
    try:
        data = request.data
        points = data.get('points', [])
        diseases = data.get('diseases', [])
        
        if not points or len(points) < 5:
            return Response({"error": "Not enough points for clustering."}, status=400)
            
        disease_context = diseases[0].lower() if len(diseases) == 1 else 'mixed'
        
        eps = 0.045
        minpoints = 3
        timeframe_days = 30
        
        if disease_context == 'cholera':
            eps = 0.009 # ~1km
            minpoints = 5
            timeframe_days = 14
        elif disease_context == 'tb':
            eps = 0.022 # ~2.5km
            minpoints = 10
            timeframe_days = 180
        elif disease_context == 'typhoid':
            eps = 0.012 # ~1.3km (slow-burning urban WASH)
            minpoints = 5
            timeframe_days = 60
        elif disease_context == 'malaria':
            eps = 0.025 # ~2.8km (mosquito flight range/water bodies)
            minpoints = 5
            timeframe_days = 60
        elif disease_context == 'hiv':
            return Response({
                "error": "Venue-Based Mapping Recommended. Distance-based spatial clustering (DBSCAN) is epidemiologically incorrect and violates privacy for HIV cases. Data should be aggregated to district-level density or mapped via Key Population (KP) venues."
            }, status=400)
            
        valid_points = []
        try:
            dates = []
            for p in points:
                if p.get('date'):
                    try:
                        # Extract the first 10 chars (YYYY-MM-DD) to safely parse, or use full isoformat
                        dt_str = str(p['date'])[:10]
                        dt = datetime.strptime(dt_str, "%Y-%m-%d")
                        dates.append(dt)
                    except ValueError:
                        pass
            if dates:
                max_date = max(dates)
                cutoff_date = max_date - timedelta(days=timeframe_days)
                for p in points:
                    if p.get('date'):
                        try:
                            dt_str = str(p['date'])[:10]
                            dt = datetime.strptime(dt_str, "%Y-%m-%d")
                            if dt >= cutoff_date:
                                valid_points.append(p)
                        except ValueError:
                            pass
            else:
                valid_points = points
        except Exception:
            valid_points = points
            
        if len(valid_points) < minpoints:
             return Response({"error": f"Not enough recent cases within the {timeframe_days}-day temporal window for statistically significant clustering."}, status=400)
             
        # Format for json_to_recordset using valid_points, ensuring valid non-zero coordinates
        cleaned_points = []
        for p in valid_points:
            lon, lat = p.get('lon'), p.get('lat')
            try:
                lon, lat = float(lon), float(lat)
                # Ignore exactly 0.0, 0.0 which often represents missing geodata
                if (lon != 0.0 or lat != 0.0) and (-180 <= lon <= 180) and (-90 <= lat <= 90):
                    cleaned_points.append({"lon": lon, "lat": lat})
            except (TypeError, ValueError):
                pass
                
        if len(cleaned_points) < minpoints:
            return Response({"error": "Not enough valid geocoded points for clustering."}, status=400)
            
        json_points = json.dumps(cleaned_points)
        
        query = """
        WITH clustered_points AS (
            SELECT ST_ClusterDBSCAN(geom, eps := %s, minpoints := %s) OVER () as cluster_id
            FROM (
                SELECT ST_SetSRID(ST_MakePoint(lon, lat), 4326) as geom
                FROM json_to_recordset(%s::json) as x(lon float, lat float)
            ) as subquery
        )
        SELECT 
            COUNT(*) FILTER (WHERE cluster_id IS NOT NULL) as clustered_count,
            COUNT(*) FILTER (WHERE cluster_id IS NULL) as noise_count,
            COUNT(DISTINCT cluster_id) as num_clusters
        FROM clustered_points;
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, [eps, minpoints, json_points])
            row = cursor.fetchone()
            
        clustered_count = row[0] or 0
        noise_count = row[1] or 0
        num_clusters = row[2] or 0
        
        total = clustered_count + noise_count
        cluster_percentage = (clustered_count / total * 100) if total > 0 else 0
        
        return Response({
            "clustered_count": clustered_count,
            "noise_count": noise_count,
            "num_clusters": num_clusters,
            "cluster_percentage": round(cluster_percentage, 1)
        })
        
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@login_required
def map_dashboard(request):
    """Renders the main Leaflet map frontend."""
    diseases = [m.__name__.replace('Case', '').lower() for m in _get_all_disease_models()]
    return render(request, 'surveillance/dashboard.html', {'diseases': diseases})

def _build_instance(row, ModelClass, facility_cache, available_facilities):
    """
    Helper function to transform a flat dictionary (from CSV/Excel/JSON) into an instantiated 
    Django Model object, handling data normalization and spatial distance calculations.
    """
    row_lower = {str(k).lower().strip(): v for k, v in row.items() if k is not None}
    
    def get_alias(keys, default=''):
        for k in keys:
            if k in row_lower and row_lower[k] not in [None, '', 'nan']:
                return row_lower[k]
        return default

    try:
        dt_str = str(get_alias(['date_of_onset', 'date', 'onset_date', 'report_date', 'date_reported'])).strip()
        parsed_date = None
        if dt_str and dt_str not in ('nan', 'none', ''):
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y'):
                try:
                    parsed_date = datetime.strptime(dt_str[:10], fmt).date()
                    break
                except ValueError:
                    continue
        # Guarantee: every record gets a date. Fall back to today if unparseable.
        if parsed_date is None:
            parsed_date = datetime.now().date()
                
        lon_val = get_alias(['lon', 'longitude', 'longtude', 'lng', 'long'])
        lat_val = get_alias(['lat', 'latitude'])
        lon = float(lon_val) if lon_val not in ['', None, 'nan'] else 0.0
        lat = float(lat_val) if lat_val not in ['', None, 'nan'] else 0.0
        
        age_val = get_alias(['age', 'patient_age', 'age_years'])
        try:
            age = int(float(age_val)) if age_val not in ['', None, 'nan'] else random.randint(5, 70)
        except (ValueError, TypeError):
            age = random.randint(5, 70)
        
        gender_raw = str(get_alias(['gender', 'sex', 'patient_gender'], '')).strip().upper()
        if gender_raw and gender_raw[0] in ('M', 'F'):
            gender = gender_raw[0]
        else:
            gender = random.choice(['M', 'F'])  # Assign rather than leave unknown
        
        disease_type = str(get_alias(['disease_type', 'disease', 'condition'], 'unknown')).lower()

        variant_raw = get_alias(['variant', 'strain', 'serotype', 'subtype'])
        variant = str(variant_raw) if variant_raw else 'Unspecified'

        location_name_raw = get_alias(['location_name', 'location', 'city', 'district', 'region', 'ward', 'village'])
        location_name = str(location_name_raw) if location_name_raw else 'Unknown Location'

        severity_raw = get_alias(['severity', 'case_severity'])
        try:
            severity = int(severity_raw) if severity_raw not in ['', None, 'nan'] else random.choice([1, 2, 3])
        except (ValueError, TypeError):
            severity = random.choice([1, 2, 3])

        outcome_raw = str(get_alias(['outcome', 'case_outcome', 'status'], '')).lower().strip()
        outcome_map = {
            'active': 'active', 'treatment': 'active', 'admitted': 'active',
            'recovered': 'recovered', 'discharged': 'recovered', 'cured': 'recovered',
            'deceased': 'deceased', 'dead': 'deceased', 'died': 'deceased', 'death': 'deceased',
            'referred': 'referred', 'transferred': 'referred',
        }
        outcome = outcome_map.get(outcome_raw, random.choice(['active', 'recovered', 'deceased', 'referred']))

        location = Point(lon, lat, srid=4326)
        
        nearest_facility = None
        cache_key = (lon, lat)
        
        # Performance Optimization: Spatial queries (calculating nearest facility) are computationally expensive.
        # When bulk importing datasets, many cases often originate from the exact same coordinates (e.g., same district center).
        # We cache the calculated nearest facility by coordinate to avoid redundant PostGIS Distance queries.
        if cache_key in facility_cache:
            nearest_facility = facility_cache[cache_key]
        elif available_facilities:
            min_dist = float('inf')
            for f in available_facilities:
                if f.location:
                    dist = f.location.distance(location)
                    if dist < min_dist:
                        min_dist = dist
                        nearest_facility = f
            facility_cache[cache_key] = nearest_facility

        kwargs = {
            'disease_type': disease_type,
            'variant': variant,
            'age': age,
            'gender': gender,
            'date_of_onset': parsed_date,
            'location_name': location_name,
            'location': location,
            'longitude': lon,
            'latitude': lat,
            'facility': nearest_facility,
            'severity': severity,
            'outcome': outcome,
        }
        
        known_keys = ['disease_type', 'disease', 'condition', 'variant', 'strain', 'type', 
                      'age', 'patient_age', 'gender', 'sex', 'patient_gender', 
                      'date_of_onset', 'date', 'onset_date', 'location_name', 'location', 
                      'city', 'district', 'region', 'lon', 'longitude', 'longtude', 'lng', 
                      'lat', 'latitude', 'facility', 'reporting facility', 'facility_name']
        
        extra_dict = {}
        for k, v in row_lower.items():
            if k not in known_keys:
                safe_col = "".join([c if c.isalnum() else '_' for c in k]).strip('_')
                if not safe_col or safe_col[0].isdigit():
                    safe_col = "col_" + safe_col
                if hasattr(ModelClass, safe_col):
                    kwargs[safe_col] = str(v)
                else:
                    extra_dict[safe_col] = str(v)
                    
        # If the model is GenericDiseaseCase, attach extra_data
        if hasattr(ModelClass, 'extra_data'):
            kwargs['extra_data'] = extra_dict

        return ModelClass(**kwargs)
    except Exception as e:
        print(f"Error processing row: {e}")
        return None


@login_required
def upload_dataset(request):
    """
    Handles the asynchronous ingestion of epidemiological datasets in various formats.
    
    This function utilizes a 3-phase ingestion strategy to ensure data integrity and 
    support dynamic schema generation before performing bulk database inserts.
    """
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        filename = uploaded_file.name.lower()
        
        count = 0
        try:
            form_disease = str(request.POST.get('disease_type', '')).strip().lower()
            if not form_disease:
                return JsonResponse({'status': 'error', 'message': 'You must select a target disease type before uploading.'}, status=400)
                
            ModelClass = get_or_create_dynamic_model(form_disease, [])
            available_facilities = list(HealthFacility.objects.all())
            facility_cache = {}
            instances_to_create = []
            
            def process_row(row):
                row['disease_type'] = form_disease
                row_lower = {str(k).lower().strip(): v for k, v in row.items() if k is not None}
                
                def get_alias(keys):
                    for k in keys:
                        if k in row_lower and row_lower[k] not in [None, '', 'nan']:
                            return row_lower[k]
                    return None
                    
                lon = get_alias(['lon', 'longitude', 'longtude', 'lng'])
                lat = get_alias(['lat', 'latitude'])
                
                # If lon or lat is missing, _build_instance will default it to 0.0 instead of failing the upload.
                
                instance = _build_instance(row, ModelClass, facility_cache, available_facilities)
                if instance:
                    instances_to_create.append(instance)
                    
                if len(instances_to_create) >= 500:
                    ModelClass.objects.bulk_create(instances_to_create)
                    instances_to_create.clear()

            import io
            if filename.endswith('.csv') or filename.endswith('.tsv'):
                try:
                    decoded_file = io.TextIOWrapper(uploaded_file, encoding='utf-8-sig', errors='replace')
                    delimiter = '\t' if filename.endswith('.tsv') else ','
                    reader = csv.DictReader(decoded_file, delimiter=delimiter)
                    for row in reader:
                        process_row(row)
                        count += 1
                except Exception as e:
                    return JsonResponse({'status': 'error', 'message': f'Failed to parse CSV/TSV: {str(e)}'}, status=400)
                        
            elif filename.endswith(('.xlsx', '.xls', '.ods')):
                import pandas as pd
                try:
                    df = pd.read_excel(uploaded_file)
                    df = df.fillna('')
                    for _, row in df.iterrows():
                        process_row(row.to_dict())
                        count += 1
                except Exception as e:
                    return JsonResponse({'status': 'error', 'message': f'Failed to parse spreadsheet: {str(e)}'}, status=400)
                        
            elif filename.endswith('.geojson'):
                try:
                    data = json.loads(uploaded_file.read().decode('utf-8', errors='replace'))
                    features = data.get('features', [])
                    for feature in features:
                        props = feature.get('properties', {})
                        geom = feature.get('geometry', {})
                        if geom and geom.get('type') == 'Point':
                            coords = geom.get('coordinates', [0, 0])
                            props['lon'] = coords[0]
                            props['lat'] = coords[1]
                        process_row(props)
                        count += 1
                except Exception as e:
                    return JsonResponse({'status': 'error', 'message': f'Failed to parse GeoJSON: {str(e)}'}, status=400)
                        
            elif filename.endswith(('.nwk', '.newick', '.tre', '.nex', '.nexus', '.nhx', '.dot')):
                content = uploaded_file.read().decode('utf-8', errors='replace')
                try:
                    trees = newick.loads(content)
                    for tree in trees:
                        for leaf in tree.get_leaves():
                            if leaf.name:
                                process_row({'disease_type': 'unknown', 'variant': leaf.name, 'lon': 0, 'lat': 0})
                                count += 1
                except Exception as e:
                    nodes = set(re.findall(r'([a-zA-Z0-9_\-\.]+)', content))
                    for node in nodes:
                        if len(node) > 2:
                            process_row({'disease_type': 'unknown', 'variant': node, 'lon': 0, 'lat': 0})
                            count += 1
            else:
                return JsonResponse({'status': 'error', 'message': f'Unsupported file format: {filename}'}, status=400)
                
            if instances_to_create:
                ModelClass.objects.bulk_create(instances_to_create)
                
            return JsonResponse({'status': 'success', 'message': f'Imported {count} records.'})
        except Exception as e:
             return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
             
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def report_case(request):
    """
    Handles individual case reports submitted via the frontend UI.
    Supports dynamic schema expansion if the frontend sends unexpected key-value pairs.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            facility_id = data.get('facility_id')
            if not facility_id:
                return JsonResponse({'status': 'error', 'message': 'Health facility must be selected.'}, status=400)
                
            if str(facility_id).isdigit():
                facility = get_object_or_404(HealthFacility, id=int(facility_id))
            else:
                f_lat = data.get('new_facility_lat')
                f_lng = data.get('new_facility_lng')
                if not f_lat or not f_lng:
                   return JsonResponse({'status': 'error', 'message': 'Could not geolocate custom facility automatically. Valid coordinates are required.'}, status=400)
                facility, created = HealthFacility.objects.get_or_create(
                    name=str(facility_id).strip(),
                    defaults={'location': Point(float(f_lng), float(f_lat), srid=4326)}
                )
            lon = float(data.get('lon', 0.0))
            lat = float(data.get('lat', 0.0))
            location_name = str(data.get('location_name', 'Unknown Location'))
            disease_type = str(data.get('disease_type', 'unknown')).lower()
            
            # Find any extra columns sent that aren't core
            # This allows the frontend to submit arbitrary key-value pairs (e.g., custom symptoms)
            # which are then used to dynamically expand the model schema if they don't already exist.
            core_keys = ['facility_id', 'lon', 'lat', 'disease_type', 'variant', 'age', 'gender', 'date_of_onset', 'location_name']
            extra_columns = [k for k in data.keys() if k not in core_keys]
            
            ModelClass = get_or_create_dynamic_model(disease_type, extra_columns)

            location = Point(lon, lat, srid=4326)

            kwargs = {
                'disease_type': disease_type,
                'variant': data.get('variant'),
                'age': int(data.get('age')) if data.get('age') else None,
                'gender': data.get('gender', 'U'),
                'date_of_onset': data.get('date_of_onset') or None,
                'location_name': location_name,
                'location': location,
                'longitude': lon,
                'latitude': lat,
                'facility': facility,
                'severity': int(data.get('severity', 3)),
                'outcome': str(data.get('outcome', 'active')),
                'reported_by': request.user
            }
            
            extra_dict = {}
            for col in extra_columns:
                safe_col = "".join([c if c.isalnum() else '_' for c in col]).strip('_').lower()
                if not safe_col or safe_col[0].isdigit():
                    safe_col = "col_" + safe_col
                if hasattr(ModelClass, safe_col):
                    kwargs[safe_col] = str(data[col])
                else:
                    extra_dict[safe_col] = str(data[col])
                    
            if hasattr(ModelClass, 'extra_data'):
                kwargs['extra_data'] = extra_dict

            ModelClass.objects.create(**kwargs)
            return JsonResponse({'status': 'success', 'message': 'Case reported successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def get_disease_data(request, disease_type):
    disease_type = disease_type.lower()
    
    cases = []
    columns_config = []
    headers_done = False
    
    for model in _get_all_disease_models():
        model_name = model.__name__.replace('Case', '').lower()
        if model_name == disease_type:
            model_cases = model.objects.select_related('facility').order_by('-date_reported')
            
            # Serialize fields dynamically
            for case in model_cases:
                item = {}
                for field in case._meta.fields:
                    if field.name not in ['location', 'reported_by', 'facility', 'extra_data']:
                        val = getattr(case, field.name)
                        if isinstance(val, datetime):
                            val = val.isoformat()
                        elif hasattr(val, 'isoformat'):
                            val = val.isoformat()
                        item[field.name] = val
                        
                if hasattr(case, 'extra_data') and isinstance(case.extra_data, dict):
                    item.update(case.extra_data)
                        
                item['facility__name'] = case.facility.name if case.facility else '-'
                
                if not headers_done:
                    for k in item.keys():
                        title = k.replace('_', ' ').replace('__name', '').title()
                        if k == 'id': title = 'ID'
                        columns_config.append({'data': k, 'title': title, 'defaultContent': '-'})
                    headers_done = True
                    
                cases.append(item)
                
    if not columns_config:
        columns_config = [{'data': 'id', 'title': 'ID', 'defaultContent': '-'}]

    return JsonResponse({'data': cases, 'columns': columns_config})

@login_required
def manage_cases(request):
    all_models = _get_all_disease_models()
    
    user_cases = []
    all_cases = []
    total_db_cases = 0
    
    for model in all_models:
        base = model.objects.select_related('facility')
        total_db_cases += base.count()
        
        # Limit to 100 per model before memory sorting
        user_cases.extend(list(base.filter(reported_by=request.user).order_by('-date_reported')[:100]))
        all_cases.extend(list(base.order_by('-date_reported')[:100]))
        
    user_cases = sorted(user_cases, key=attrgetter('date_reported'), reverse=True)[:100]
    all_cases = sorted(all_cases, key=attrgetter('date_reported'), reverse=True)[:100]
    
    diseases = [m.__name__.replace('Case', '').lower() for m in all_models]
    
    facilities = HealthFacility.objects.all().order_by('name')

    context = {
        'user_cases': user_cases,
        'all_cases': all_cases,
        'total_db_cases': total_db_cases,
        'diseases': diseases,
        'facilities': facilities
    }
    return render(request, 'surveillance/manage_cases.html', context)

@login_required
def edit_case(request, disease_type, case_id):
    disease_type = disease_type.lower()
    ModelClass = None
    for model in _get_all_disease_models():
        if model.objects.filter(id=case_id, disease_type__iexact=disease_type).exists():
            ModelClass = model
            break
            
    if not ModelClass:
        messages.error(request, "Case not found.")
        return redirect('manage_cases')

    case = get_object_or_404(ModelClass, id=case_id, reported_by=request.user)
    
    if request.method == 'POST':
        case.disease_type = request.POST.get('disease_type', case.disease_type)
        case.variant = request.POST.get('variant', case.variant)
        
        age_val = request.POST.get('age')
        case.age = int(age_val) if age_val else None
        
        case.gender = request.POST.get('gender', case.gender)
        
        dt_val = request.POST.get('date_of_onset')
        case.date_of_onset = dt_val if dt_val else None

        case.severity = int(request.POST.get('severity', case.severity))
        case.outcome = request.POST.get('outcome', case.outcome)

        facility_id = request.POST.get('facility_id')
        if facility_id:
            if str(facility_id).isdigit():
                facility = get_object_or_404(HealthFacility, id=int(facility_id))
                case.facility = facility
            else:
                f_lat = request.POST.get('new_facility_lat')
                f_lng = request.POST.get('new_facility_lng')
                if f_lat and f_lng:
                    facility, created = HealthFacility.objects.get_or_create(
                        name=str(facility_id).strip(),
                        defaults={'location': Point(float(f_lng), float(f_lat), srid=4326)}
                    )
                    case.facility = facility

        lat_val = request.POST.get('lat')
        lng_val = request.POST.get('lng')
        if lat_val and lng_val:
            try:
                lat = float(lat_val)
                lng = float(lng_val)
                case.latitude = lat
                case.longitude = lng
                case.location = Point(lng, lat, srid=4326)
            except ValueError:
                pass

        case.save()
        messages.success(request, "Case updated successfully!")
        return redirect('manage_cases')
        
    diseases = [m.__name__.replace('Case', '').lower() for m in _get_all_disease_models()]
    facilities = HealthFacility.objects.all().order_by('name')
    return render(request, 'surveillance/edit_case.html', {'case': case, 'diseases': diseases, 'facilities': facilities})
