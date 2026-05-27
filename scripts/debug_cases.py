import os
import django

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

import logging
logging.disable(logging.CRITICAL)

from django.test import Client
import traceback

c = Client()
try:
    response = c.get('/api/cases/', HTTP_HOST='localhost')
    print('STATUS:', response.status_code)
    if response.status_code == 500:
        print('DUMPING HTML ERROR ->')
        with open('err_dump.html', 'w', encoding='utf-8') as f:
            f.write(response.content.decode('utf-8'))
        print("Wrote error to err_dump.html. Finding traceback...")
        import re
        html = response.content.decode('utf-8')
        match = re.search(r'<textarea id="traceback_area".*?>(.*?)</textarea>', html, re.DOTALL)
        if match:
            print(match.group(1))
        else:
            print("No traceback textarea found.")
    else:
        print("Body preview:", response.content.decode('utf-8')[:200])
except Exception as e:
    print('EXCEPTION OCCURRED:')
    traceback.print_exc()
