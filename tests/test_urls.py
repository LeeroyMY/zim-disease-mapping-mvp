from django.test import SimpleTestCase
from django.urls import reverse, resolve

class UrlsTestCase(SimpleTestCase):
    def test_url_resolutions(self):
        self.assertEqual(reverse('root_redirect'), '/')
        self.assertEqual(reverse('login'), '/accounts/login/')
        self.assertEqual(reverse('dashboard_root'), '/dashboard/')
        self.assertEqual(reverse('manage_cases'), '/cases/manage/')
        self.assertEqual(reverse('get_all_cases'), '/api/cases/')
        self.assertEqual(reverse('get_regions'), '/api/regions/')
        self.assertEqual(reverse('upload_dataset'), '/api/upload/')
        self.assertEqual(reverse('report_case'), '/api/report/')
        self.assertEqual(reverse('spatial_clustering'), '/api/spatial-clustering/')
