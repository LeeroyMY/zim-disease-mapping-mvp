from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from surveillance.models import GenericDiseaseCase

class GenericUploadTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='genericuser', password='password')
        self.client = Client()
        self.client.force_login(self.user)

    def test_generic_disease_upload_with_extra_fields(self):
        csv_content = b"lat,lon,date_of_onset,facility,disease_type,variant,custom_symptom,blood_pressure\n-19.0,29.0,2026-03-01,Test Clinic,ebola,zaire,fever,120/80"
        file = SimpleUploadedFile("test_ebola.csv", csv_content, content_type="text/csv")
        response = self.client.post('/api/upload/', {
            'file': file,
            'disease_type': 'ebola'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')
        cases = GenericDiseaseCase.objects.filter(disease_type='ebola')
        self.assertTrue(cases.exists())
        first_case = cases.first()
        self.assertIn('blood_pressure', first_case.extra_data)
        self.assertEqual(first_case.extra_data['blood_pressure'], '120/80')
