from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point, MultiPolygon
import json

from surveillance.models import CholeraCase, HealthFacility, AdministrativeBoundary

class ZimEpiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'adminpass')
        self.health_user = User.objects.create_user('user1', 'user1@test.com', 'userpass')
        
        self.facility = HealthFacility.objects.create(
            name="Test Clinic",
            location=Point(30.0, -18.0)
        )
        
        self.boundary = AdministrativeBoundary.objects.create(
            name="Test District",
            level="district",
            geom=MultiPolygon(Point(30.0, -18.0).buffer(0.1)) # dummy multipolygon
        )
        
        self.cholera_case = CholeraCase.objects.create(
            disease_type="cholera",
            variant="O1 Inaba",
            age=25,
            gender="F",
            date_of_onset="2026-01-01",
            location_name="Harare",
            longitude=31.0,
            latitude=-17.8,
            location=Point(31.0, -17.8, srid=4326),
            facility=self.facility,
            severity=2,
            outcome="active",
            reported_by=self.health_user
        )

    def test_login_routing_admin(self):
        self.client.login(username='admin', password='adminpass')
        response = self.client.get(reverse('dashboard_root'))
        self.assertEqual(response.status_code, 200)

    def test_login_routing_health_personnel(self):
        self.client.login(username='user1', password='userpass')
        response = self.client.get(reverse('manage_cases')) # health personnel dashboard
        self.assertEqual(response.status_code, 200)

    def test_api_cases_endpoint(self):
        response = self.client.get('/api/cases/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['type'], 'FeatureCollection')
        self.assertTrue(len(data['features']) > 0)
        
        # Test geomasking - the point shouldn't be exactly 31.0, -17.8
        coords = data['features'][0]['geometry']['coordinates']
        self.assertNotEqual(coords, [31.0, -17.8])
        
    def test_api_boundaries_endpoint(self):
        response = self.client.get('/api/boundaries/?tolerance=0.01')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['type'], 'FeatureCollection')

    def test_api_latest_cases(self):
        response = self.client.get('/api/latest-cases/?since=2026-01-01T00:00:00Z')
        self.assertEqual(response.status_code, 200)

    def test_spatial_clustering_valid(self):
        points = [{"lon": 31.0, "lat": -17.8, "date": "2026-01-01"} for _ in range(6)]
        response = self.client.post('/api/spatial-clustering/', json.dumps({"points": points, "diseases": ["cholera"]}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        
    def test_spatial_clustering_invalid_empty(self):
        response = self.client.post('/api/spatial-clustering/', json.dumps({"points": [], "diseases": ["cholera"]}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        
    def test_case_creation_api(self):
        self.client.login(username='user1', password='userpass')
        payload = {
            "facility_id": self.facility.id,
            "disease_type": "cholera",
            "variant": "O1 Ogawa",
            "age": 44,
            "gender": "M",
            "date_of_onset": "2026-03-20",
            "lat": "-17.82",
            "lon": "31.05",
            "location_name": "Test Location",
            "severity": 3,
            "outcome": "active"
        }
        response = self.client.post('/api/report/', json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CholeraCase.objects.filter(variant="O1 Ogawa").exists())
        
        # Test Case UUID generation
        new_case = CholeraCase.objects.filter(variant="O1 Ogawa").first()
        self.assertIsNotNone(new_case.patient_id)

    def test_case_editing_view(self):
        self.client.login(username='user1', password='userpass')
        response = self.client.post(f'/cases/edit/cholera/{self.cholera_case.id}/', {
            'disease_type': 'cholera',
            'variant': 'O1 Inaba',
            'age': 26, # changed
            'severity': 3
        })
        self.cholera_case.refresh_from_db()
        self.assertEqual(self.cholera_case.age, 26)
