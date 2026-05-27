from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers
from .models import CholeraCase, HIVCase, TBCase, AdministrativeBoundary, HealthFacility

class BaseDiseaseCaseSerializer(GeoFeatureModelSerializer):
    facility_name = serializers.SerializerMethodField()

    def get_facility_name(self, obj):
        if obj.facility:
            return obj.facility.name
        return None

    class Meta:
        geo_field = 'location'
        fields = (
            'id', 'disease_type', 'variant', 'category', 'severity', 
            'outcome', 'date_reported', 'date_of_onset', 'facility_name',
            'location_name', 'age', 'gender'
        )

class CholeraCaseSerializer(BaseDiseaseCaseSerializer):
    class Meta(BaseDiseaseCaseSerializer.Meta):
        model = CholeraCase

class HIVCaseSerializer(BaseDiseaseCaseSerializer):
    class Meta(BaseDiseaseCaseSerializer.Meta):
        model = HIVCase

class TBCaseSerializer(BaseDiseaseCaseSerializer):
    class Meta(BaseDiseaseCaseSerializer.Meta):
        model = TBCase

class AdministrativeBoundarySerializer(GeoFeatureModelSerializer):
    class Meta:
        model = AdministrativeBoundary
        geo_field = 'geom'
        fields = ('id', 'name', 'code', 'level')

class HealthFacilitySerializer(GeoFeatureModelSerializer):
    class Meta:
        model = HealthFacility
        geo_field = 'location'
        fields = ('id', 'name', 'district_name', 'province')