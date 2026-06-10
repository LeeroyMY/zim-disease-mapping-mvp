import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
from surveillance.models import HealthFacility

facilities_count = HealthFacility.objects.count()

query = """
    WITH clustered AS (
        SELECT ST_ClusterDBSCAN(location::geometry, 0.045, 3) OVER() AS cluster_id
        FROM surveillance_genericdiseasecase
        WHERE location IS NOT NULL
    )
    SELECT 
        COUNT(*) as total_points,
        COUNT(CASE WHEN cluster_id IS NULL THEN 1 END) as noise_count,
        COUNT(CASE WHEN cluster_id IS NOT NULL THEN 1 END) as clustered_count,
        COUNT(DISTINCT cluster_id) as num_clusters,
        MAX(cluster_size) as largest_cluster
    FROM (
        SELECT cluster_id, COUNT(*) OVER(PARTITION BY cluster_id) as cluster_size
        FROM clustered
    ) sub;
"""

times = []
for i in range(3):
    start = time.time()
    with connection.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchone()
    end = time.time()
    times.append(int((end - start) * 1000))

print('Health Facilities:', facilities_count)
print('Results:', result)
print('Times:', times)
