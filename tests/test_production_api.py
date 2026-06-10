from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
import json

class ProductionAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

    def test_get_all_cases_endpoint(self):
        url = reverse('get_all_cases')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('type', data)
        self.assertEqual(data['type'], 'FeatureCollection')
        self.assertIn('features', data)
        self.assertIsInstance(data['features'], list)

    def test_get_latest_cases_endpoint(self):
        url = reverse('get_latest_cases')
        response = self.client.get(url + '?since=2024-01-01T00:00:00Z')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('type', data)
        self.assertEqual(data['type'], 'FeatureCollection')
        self.assertIn('features', data)

    def test_spatial_clustering_invalid_payload(self):
        url = reverse('spatial_clustering')
        payload = {"points": "not_an_array", "diseases": "not_an_array"}
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], "Invalid payload format. 'points' and 'diseases' must be arrays.")
        
    def test_spatial_clustering_insufficient_points(self):
        url = reverse('spatial_clustering')
        payload = {"points": [], "diseases": ["cholera"]}
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], "Not enough points for clustering.")
