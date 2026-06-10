"""
Surveillance Models Module.

This module defines the core database schemas for the infectious diseases mapping system.
It utilizes Django's ORM integrated with PostGIS for spatial data handling.
The architectural focus is on mitigating the Modifiable Areal Unit Problem (MAUP)
by treating all cases and facilities as raw coordinate points (PointField) rather than 
aggregating them into administrative zones. 

Disease models are designed to be dynamic, inheriting from an abstract BaseDiseaseCase,
allowing the system to accept new disease types and arbitrary columns without migrations.
"""

import uuid
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GistIndex # Explicit spatial index import

# 1. ADMINISTRATIVE BOUNDARIES (The "Control Group" for MAUP Analysis)
class AdministrativeBoundary(models.Model):
    """
    Represents political or administrative regions (e.g., Provinces, Districts).
    
    Architectural Note:
    While these boundaries exist in the system, they are primarily used for reference,
    filtering, and baseline comparison. They are intentionally NOT used for aggregating 
    disease case data to avoid the Modifiable Areal Unit Problem (MAUP).
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True, help_text="P-Code or District ID") 
    
    LEVEL_CHOICES = [
        ('province', 'Province'),
        ('district', 'District'),
    ]
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    geom = gis_models.MultiPolygonField(srid=4326)

    class Meta:
        verbose_name_plural = "Administrative Boundaries"

    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"

# 2. HEALTH FACILITIES
class HealthFacility(models.Model):
    """
    Represents a hospital, clinic, or reporting center.
    
    Facilities act as the primary nodes where cases are reported. The spatial
    location (PointField) allows the system to calculate distances between patient
    residences and reporting centers.
    """
    name = models.CharField(max_length=200)
    district_name = models.CharField(max_length=100, blank=True) 
    province = models.CharField(max_length=100, blank=True)
    location = gis_models.PointField(srid=4326, geography=True) 

    class Meta:
        verbose_name_plural = "Health Facilities"

    def __str__(self):
        return self.name

# 3. DISEASE CASES (The "Intervention")
class BaseDiseaseCase(models.Model):
    """
    Abstract base class for all epidemiological cases.
    
    Architectural Note:
    This model is abstract. Concrete tables are generated dynamically at runtime 
    (e.g., `disease_cholera`) based on the dataset being uploaded. This prevents 
    the need for hardcoded models and schema migrations for every new outbreak or disease.
    
    Spatial Optimization:
    The `location` field represents the raw point coordinates of the case. It is 
    indexed with a `GistIndex` to ensure rapid spatial queries (bounding boxes, KDE).
    """
    # ANONYMIZATION
    patient_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # TEXT LOCATION NAME
    location_name = models.CharField(max_length=255, blank=True, null=True, help_text="e.g., Patient Home, Makonde District")

    # --- NEW: DEMOGRAPHICS ---
    age = models.IntegerField(null=True, blank=True, help_text="Age in years")
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('U', 'Unknown')]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U')

    longitude = models.FloatField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)

    # CHOICES
    CATEGORY_CHOICES = [
        ('waterborne', 'Waterborne & Enteric'),
        ('vector', 'Vector-Borne'),
        ('vaccine', 'Vaccine-Preventable'),
        ('vhf', 'Viral Haemorrhagic Fevers'),
        ('zoonotic', 'Zoonotic'),
        ('respiratory', 'Respiratory & Airborne'),
        ('other', 'Other Notifiable'),
    ]

    # Removed predefined DISEASE_CHOICES to allow dynamic disease types

    SEVERITY_CHOICES = [
        (1, 'Suspected'),
        (2, 'Probable'),
        (3, 'Confirmed'),
    ]

    OUTCOME_CHOICES = [
        ('active', 'Active / Treatment'),
        ('recovered', 'Recovered'),
        ('deceased', 'Deceased'),
        ('referred', 'Referred Out'),
    ]

    # FIELDS
    disease_type = models.CharField(max_length=100)
    variant = models.CharField(max_length=100, blank=True, null=True, help_text="Specific strain or variant, e.g., Cholera O1 Ogawa, MDR-TB")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', editable=False)
    facility = models.ForeignKey(HealthFacility, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_cases')
    reported_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_reported_cases')
    
    date_reported = models.DateTimeField(auto_now_add=True)
    date_of_onset = models.DateField(null=True, blank=True, help_text="Date symptoms started")

    severity = models.IntegerField(choices=SEVERITY_CHOICES, default=1)
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, default='active')

    location = gis_models.PointField(srid=4326, geography=True) # Geocoded location of the case (e.g., patient home)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['disease_type']),
            models.Index(fields=['date_of_onset']),
            models.Index(fields=['date_reported']),
            models.Index(fields=['facility']),
            GistIndex(fields=['location']), # Explicit spatial index for performance
        ]

    def save(self, *args, **kwargs):
        """
        Overrides the standard save method to automatically assign broad epidemiological
        categories based on the specific disease_type string. This aids in high-level filtering.
        """
        if self.disease_type == 'cholera':
            self.category = 'waterborne'
        elif self.disease_type == 'tb':
            self.category = 'respiratory'
        elif self.disease_type == 'hiv':
            self.category = 'other'
        elif self.disease_type == 'malaria':
            self.category = 'vector'
        elif self.disease_type == 'typhoid':
            self.category = 'waterborne'
        else:
            self.category = 'other'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.disease_type.title()} - {str(self.patient_id)[:8]}"

class CholeraCase(BaseDiseaseCase):
    class Meta(BaseDiseaseCase.Meta):
        verbose_name_plural = "Cholera Cases"

class HIVCase(BaseDiseaseCase):
    class Meta(BaseDiseaseCase.Meta):
        verbose_name_plural = "HIV Cases"

class TBCase(BaseDiseaseCase):
    class Meta(BaseDiseaseCase.Meta):
        verbose_name_plural = "TB Cases"

class MalariaCase(BaseDiseaseCase):
    class Meta(BaseDiseaseCase.Meta):
        verbose_name_plural = "Malaria Cases"

class TyphoidCase(BaseDiseaseCase):
    class Meta(BaseDiseaseCase.Meta):
        verbose_name_plural = "Typhoid Cases"

class GenericDiseaseCase(BaseDiseaseCase):
    """
    A concrete model for dynamically handling any disease type not explicitly 
    defined (like Cholera, HIV, TB). Extra columns are safely stored in a JSONB 
    field instead of requiring dangerous runtime table creation.
    """
    extra_data = models.JSONField(default=dict, blank=True, help_text="Stores arbitrary dynamic columns from CSV datasets.")

    class Meta(BaseDiseaseCase.Meta):
        verbose_name_plural = "Generic Disease Cases"
