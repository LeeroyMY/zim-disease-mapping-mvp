import os
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from surveillance.models import TBCase, HealthFacility

class TBUploadAndMappingTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username='tb_admin', email='tb@test.com', password='password')
        self.client = Client()
        self.client.force_login(self.user)

    def test_upload_sample_tb_dataset(self):
        csv_path = r"C:\Users\user\.gemini\antigravity\brain\f4357fb2-b2ee-4ca5-b410-b9eddc80f95a\.user_uploaded\media_1793588489337_89727769.csv"
        self.assertTrue(os.path.exists(csv_path), "Sample CSV file should exist")

        with open(csv_path, 'rb') as f:
            file_content = f.read()

        uploaded = SimpleUploadedFile("rrtb_sample_100_rows.csv", file_content, content_type="text/csv")
        response = self.client.post('/api/upload/', {
            'file': uploaded,
            'disease_type': 'tb'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertEqual(data.get('records_imported'), 100)

        # Check DB instances
        total_cases = TBCase.objects.count()
        self.assertEqual(total_cases, 100)

        # Verify variants
        rr_cases = TBCase.objects.filter(variant='RR-TB')
        sens_cases = TBCase.objects.filter(variant='Rif-Sensitive')
        self.assertTrue(rr_cases.exists(), "Should have RR-TB cases")
        self.assertTrue(sens_cases.exists(), "Should have Rif-Sensitive cases")

        # Check specific row 1 (record_id 56541)
        # record_id 56541: test_date: 2025-01-15, facility: MASHABA CLINIC, sex: Female, age: 30.0, rif_result: Not Detected, rr_tb: 0
        case_56541 = TBCase.objects.filter(extra_data__record_id='56541').first()
        self.assertIsNotNone(case_56541)
        self.assertEqual(case_56541.variant, 'Rif-Sensitive')
        self.assertEqual(case_56541.gender, 'F')
        self.assertEqual(case_56541.age, 30)
        self.assertEqual(str(case_56541.date_of_onset), '2025-01-15')
        self.assertIn('extra_data', dir(case_56541))
        self.assertEqual(case_56541.extra_data.get('assay'), 'Xpert (unspecified)')
        self.assertEqual(case_56541.extra_data.get('rif_result'), 'Not Detected')
        self.assertEqual(case_56541.extra_data.get('facility_name'), 'MASHABA CLINIC')

        # Check row 2 (record_id 23633)
        # record_id 23633: rif_result: Detected, rr_tb: 1
        case_23633 = TBCase.objects.filter(extra_data__record_id='23633').first()
        self.assertIsNotNone(case_23633)
        self.assertEqual(case_23633.variant, 'RR-TB')
        self.assertEqual(case_23633.severity, 3)

        # Check GeoJSON endpoint
        cases_res = self.client.get('/api/cases/')
        self.assertEqual(cases_res.status_code, 200)
        features = cases_res.json().get('features', [])
        
        # Verify no 0,0 points are mapped
        for f in features:
            coords = f['geometry']['coordinates']
            self.assertFalse(coords[0] == 0.0 and coords[1] == 0.0)
            if f['properties'].get('record_id') == '56541':
                self.assertEqual(f['properties'].get('variant'), 'Rif-Sensitive')
                self.assertEqual(f['properties'].get('facility__name'), 'MASHABA CLINIC')
                self.assertEqual(f['properties'].get('assay'), 'Xpert (unspecified)')
                self.assertEqual(f['properties'].get('rif_result'), 'Not Detected')

        # Test spatial clustering with TB payload
        tb_points = []
        for f in features:
            if f['properties'].get('disease_type') == 'tb':
                tb_points.append({
                    "lon": f['geometry']['coordinates'][0],
                    "lat": f['geometry']['coordinates'][1],
                    "date": f['properties'].get('date_of_onset'),
                    "disease": "tb"
                })

        self.assertTrue(len(tb_points) >= 10)
        cluster_res = self.client.post('/api/spatial-clustering/', {
            "points": tb_points,
            "diseases": ["tb"]
        }, content_type='application/json')
        self.assertEqual(cluster_res.status_code, 200)
        cluster_data = cluster_res.json()
        self.assertIn('clustered_count', cluster_data)
        self.assertIn('noise_count', cluster_data)
        self.assertIn('num_clusters', cluster_data)
        self.assertIn('cluster_percentage', cluster_data)

