import requests
import json
import base64

session = requests.Session()
login_url = 'http://localhost:8000/admin/login/'
r = session.get(login_url)
if 'csrftoken' in session.cookies:
    csrftoken = session.cookies['csrftoken']
else:
    print("Could not get CSRF token")
    exit(1)

login_data = {
    'username': 'admin',
    'password': 'admin',
    'csrfmiddlewaretoken': csrftoken,
    'next': '/admin/'
}
p = session.post(login_url, data=login_data, headers={'Referer': login_url})

# 1. Test /api/cases/
api_cases = session.get('http://localhost:8000/api/cases/')
print(f"Cases API (/api/cases/): {api_cases.status_code}")
if api_cases.status_code == 200:
    data = api_cases.json()
    print(f"  Returned features count: {len(data.get('features', []))}")

# 2. Test /api/table-cases/tb/
api_table_tb = session.get('http://localhost:8000/api/table-cases/tb/')
print(f"Table TB API: {api_table_tb.status_code}")
if api_table_tb.status_code == 200:
    data = api_table_tb.json()
    print(f"  Returned TB data count: {len(data.get('data', []))}")

# 3. Test /api/upload/
csv_content = b"disease_type,location_name,lat,lon,age,gender,severity,outcome\ncholera,Harare,-17.82,31.05,25,M,3,active\nhiv,Harare,-17.82,31.05,30,F,3,active"
upload_url = 'http://localhost:8000/api/upload/'
files = {'file': ('test_upload.csv', csv_content, 'text/csv')}
# Since upload API might be CSRF exempt but we are in session:
upload_res = session.post(upload_url, files=files, headers={'X-CSRFToken': csrftoken})
print(f"Upload API: {upload_res.status_code} - Response: {upload_res.text}")

# 4. Test /api/report/
report_payload = {
    "disease_type": "cholera",
    "variant": "O1 Ogawa",
    "age": 44,
    "gender": "F",
    "date_of_onset": "2026-03-20",
    "lat": -17.82,
    "lon": 31.05
}
report_res = session.post('http://localhost:8000/api/report/', json=report_payload, headers={'X-CSRFToken': csrftoken})
print(f"Report API: {report_res.status_code} - Response: {report_res.text}")

print("Testing complete.")
