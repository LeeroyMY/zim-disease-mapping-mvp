import os
import subprocess
from django.conf import settings
from django.apps import apps
from django.db import models
from .models import BaseDiseaseCase

def get_or_create_dynamic_model(disease_type, extra_columns):
    """
    Returns the appropriate Django model class for a given disease type.

    Routes the five core diseases to their dedicated concrete models.
    Any other disease type falls back to GenericDiseaseCase, which stores
    arbitrary extra columns in a JSONB field to avoid schema migrations.
    """
    class_name_lower = "".join([c for c in disease_type.title() if c.isalpha()]).lower() + "case"

    MODEL_MAP = {
        'choleracase':  'choleracase',
        'hivcase':      'hivcase',
        'tbcase':       'tbcase',
        'malariacase':  'malariacase',
        'typhoidcase':  'typhoidcase',
    }

    app_label = MODEL_MAP.get(class_name_lower, 'genericdiseasecase')
    return apps.get_model('surveillance', app_label)

import math
import random

def get_geomasking_radii(case):
    """
    Returns r_min and r_max (in meters) based on the case's geographical context.
    Urban areas get tighter radii (250m - 750m) due to higher population density.
    Rural areas get wider radii (750m - 2500m) to preserve k-anonymity.
    """
    urban_areas = ['harare', 'bulawayo']
    
    # Try to determine if the case is in an urban area
    is_urban = False
    
    if case.facility and case.facility.province:
        prov = case.facility.province.lower()
        if any(urban_center in prov for urban_center in urban_areas):
            is_urban = True
            
    if case.location_name:
        loc = case.location_name.lower()
        if any(urban_center in loc for urban_center in urban_areas):
            is_urban = True

    if is_urban:
        return 250, 750
    else:
        # Default for rural/sparse areas
        return 750, 2500

def apply_donut_geomasking(lon, lat, r_min, r_max, seed_val=None):
    """
    Perturbs coordinates using Donut Geomasking (Armstrong, Rushton and Zimmerman, 1999).
    Displaces the point by a random distance between r_min and r_max meters,
    in a random direction (0 to 2π).
    
    Args:
        lon (float): Original longitude
        lat (float): Original latitude
        r_min (float): Minimum displacement in meters
        r_max (float): Maximum displacement in meters
        seed_val (str, optional): A seed (like patient UUID) to ensure deterministic jitter.
        
    Returns:
        tuple: (masked_lon, masked_lat)
    """
    if lon == 0.0 and lat == 0.0:
        return 0.0, 0.0
        
    # Seed the random number generator if a seed is provided
    # so that the same point always displaces to the same masked location
    if seed_val:
        random.seed(str(seed_val))
        
    # Draw random distance and angle
    R = random.uniform(r_min, r_max)
    theta = random.uniform(0, 2 * math.pi)
    
    # Calculate displacement in meters
    dx = R * math.cos(theta)
    dy = R * math.sin(theta)
    
    # Convert meters to decimal degrees (approximate)
    # 1 degree of latitude is ~111,111 meters
    delta_lat = dy / 111111.0
    
    # 1 degree of longitude is ~111,111 meters * cos(latitude)
    lat_rad = math.radians(lat)
    if math.cos(lat_rad) == 0:
        delta_lon = 0
    else:
        delta_lon = dx / (111111.0 * math.cos(lat_rad))
    
    masked_lon = lon + delta_lon
    masked_lat = lat + delta_lat
    
    # Reset the random seed to system time so other random operations aren't affected
    if seed_val:
        random.seed()
        
    return masked_lon, masked_lat
