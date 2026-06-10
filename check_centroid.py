import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

query = """
WITH valid_cases AS (
    SELECT longitude, latitude 
    FROM surveillance_choleracase
    WHERE longitude != 0.0 AND latitude != 0.0 AND longitude IS NOT NULL AND latitude IS NOT NULL
    UNION ALL
    SELECT longitude, latitude 
    FROM surveillance_tbcase
    WHERE longitude != 0.0 AND latitude != 0.0 AND longitude IS NOT NULL AND latitude IS NOT NULL
),
clustered_points AS (
    SELECT ST_ClusterDBSCAN(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326), eps := 0.045, minpoints := 3) OVER () as cluster_id,
           longitude, latitude, ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) as geom
    FROM valid_cases
),
cluster_stats AS (
    SELECT cluster_id, COUNT(*) as pt_count,
           ST_Y(ST_Centroid(ST_Collect(geom))) as centroid_lat,
           ST_X(ST_Centroid(ST_Collect(geom))) as centroid_lon
    FROM clustered_points
    WHERE cluster_id IS NOT NULL
    GROUP BY cluster_id
)
SELECT cluster_id, pt_count, centroid_lat, centroid_lon
FROM cluster_stats
ORDER BY pt_count DESC
LIMIT 1;
"""

with connection.cursor() as cursor:
    cursor.execute(query)
    row = cursor.fetchone()
    if row:
        print(f"Cluster ID: {row[0]}, Count: {row[1]}, Centroid: lat {row[2]}, lon {row[3]}")
    else:
        print("No clusters found")
