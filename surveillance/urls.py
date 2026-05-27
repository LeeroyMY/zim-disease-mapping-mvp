from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    get_all_cases, 
    get_latest_cases,
    get_regions,
    AdministrativeBoundaryViewSet, 
    HealthFacilityViewSet, 
    map_dashboard, 
    upload_dataset, 
    report_case,
    manage_cases,
    edit_case,
    get_disease_data,
    calculate_spatial_clustering
)

router = DefaultRouter()
router.register(r'boundaries', AdministrativeBoundaryViewSet)
router.register(r'facilities', HealthFacilityViewSet)

urlpatterns = [
    # GeoJSON Data endpoints
    path('api/', include(router.urls)), 
    path('api/cases/', get_all_cases, name='get_all_cases'),
    path('api/latest-cases/', get_latest_cases, name='get_latest_cases'),
    path('api/regions/', get_regions, name='get_regions'),
    
    # Custom API endpoints
    path('api/upload/', upload_dataset, name='upload_dataset'),
    path('api/report/', report_case, name='report_case'),
    path('api/table-cases/<str:disease_type>/', get_disease_data, name='get_disease_data'),
    path('api/spatial-clustering/', calculate_spatial_clustering, name='spatial_clustering'),
    
    # Case Management Pages
    path('cases/manage/', manage_cases, name='manage_cases'),
    path('cases/edit/<str:disease_type>/<int:case_id>/', edit_case, name='edit_case'),
    
    # Map webpages
    path('dashboard/', map_dashboard, name='dashboard_root'), 
]