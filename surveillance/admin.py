from django.contrib.gis import admin
from .models import CholeraCase, HIVCase, TBCase, HealthFacility, AdministrativeBoundary

@admin.register(AdministrativeBoundary)
class AdministrativeBoundaryAdmin(admin.GISModelAdmin):
    list_display = ('name', 'level', 'code')
    list_filter = ('level',) 
    search_fields = ('name', 'code')

@admin.register(HealthFacility)
class HealthFacilityAdmin(admin.GISModelAdmin):
    list_display = ('name', 'district_name', 'province')
    search_fields = ('name', 'district_name')

class BaseDiseaseCaseAdmin(admin.GISModelAdmin):
    # Django to use our custom HTML page for the Search Box
    change_form_template = 'admin/custom_map_change_form.html'

    list_display = ('patient_id', 'disease_type', 'variant', 'severity', 'outcome', 'age', 'gender', 'get_longitude', 'get_latitude', 'facility', 'date_of_onset')
    
    def get_longitude(self, obj):
        return round(obj.location.x, 5) if obj.location else None
    get_longitude.short_description = 'Longitude'

    def get_latitude(self, obj):
        return round(obj.location.y, 5) if obj.location else None
    get_latitude.short_description = 'Latitude'
    list_filter = ('category', 'disease_type', 'variant', 'severity', 'outcome', 'gender', 'facility')
    search_fields = ('disease_type', 'variant', 'patient_id', 'location_name')
    readonly_fields = ('category', 'date_reported', 'patient_id')
    
    autocomplete_fields = ('facility',)
    
    fieldsets = (
        ('Identification (Anonymized)', {
            'fields': ('patient_id',)
        }),
        ('Demographics', {   
            'fields': ('age', 'gender')
        }),
        ('Clinical Details', {
            'fields': ('disease_type', 'variant', 'category', 'severity', 'outcome', 'date_of_onset')
        }),
        ('Location Context', {
            'fields': ('location_name', 'location', 'facility')
        }),
        ('System Metadata', {
            'fields': ('date_reported',),
            'classes': ('collapse',), 
        }),
    )

from django.apps import apps
from .models import BaseDiseaseCase

for model in apps.get_models():
    if issubclass(model, BaseDiseaseCase) and model is not BaseDiseaseCase:
        try:
            admin.site.register(model, BaseDiseaseCaseAdmin)
        except admin.sites.AlreadyRegistered:
            pass