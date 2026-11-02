from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from surveillance.models import CholeraCase

class UploadTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='uploaduser', password='password')
        self.client = Client()
        self.client.force_login(self.user)

    def test_csv_upload_cholera(self):
        csv_content = b"lat,lon,date_of_onset,facility,disease_type,variant\n-19.0,29.0,2026-03-01,Test Clinic,cholera,O1 Inaba"
        file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        response = self.client.post('/api/upload/', {
            'file': file,
            'disease_type': 'cholera'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertTrue(CholeraCase.objects.filter(variant='O1 Inaba').exists())
