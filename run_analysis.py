import os
import django
import sys
import json
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
from surveillance.models import AdministrativeBoundary
from surveillance.serializers import AdministrativeBoundarySerializer
from rest_framework.renderers import JSONRenderer

# 1. Payload analysis
print("=== PAYLOAD ANALYSIS ===")
boundaries = AdministrativeBoundary.objects.all()
serializer = AdministrativeBoundarySerializer(boundaries, many=True)
start_time = time.time()
data = serializer.data
json_bytes = JSONRenderer().render(data)
end_time = time.time()
print(f"Original /api/boundaries/ payload size: {len(json_bytes) / (1024*1024):.2f} MB")
print(f"Original serialization time: {end_time - start_time:.4f} seconds")

# 2. DBSCAN Sensitivity Analysis
print("\n=== DBSCAN SENSITIVITY GRID ===")
# Generate some synthetic points to use for testing if we can't find cholera cases easily.
# Actually let's try to query the database using the same query as in views.py

# First get some points to use.
# Since it's synthetic data, we can just grab cholera points
from surveillance.models import CholeraCase
cases = CholeraCase.objects.all()[:500] 
points = [{"lon": float(c.longitude), "lat": float(c.latitude)} for c in cases if c.longitude and c.latitude]

if not points:
    print("No cholera cases found to test DBSCAN.")
else:
    print(f"Testing with {len(points)} points.")
    json_points = json.dumps(points)
    
    grids = [
        (0.02, 3),
        (0.02, 5),
        (0.045, 3),
        (0.045, 5),
    ]
    
    query = """
    WITH clustered_points AS (
        SELECT ST_ClusterDBSCAN(geom, eps := %s, minpoints := %s) OVER () as cluster_id, geom
        FROM (
            SELECT ST_SetSRID(ST_MakePoint(lon, lat), 4326) as geom
            FROM json_to_recordset(%s::json) as x(lon float, lat float)
        ) as subquery
    )
    SELECT 
        COUNT(*) FILTER (WHERE cluster_id IS NOT NULL) as clustered_count,
        COUNT(*) FILTER (WHERE cluster_id IS NULL) as noise_count,
        COUNT(DISTINCT cluster_id) as num_clusters
    FROM clustered_points;
    """
    
    for eps, minp in grids:
        start_time = time.time()
        with connection.cursor() as cursor:
            cursor.execute(query, [eps, minp, json_points])
            row = cursor.fetchone()
        end_time = time.time()
        clustered_count = row[0] or 0
        noise_count = row[1] or 0
        num_clusters = row[2] or 0
        total = clustered_count + noise_count
        noise_pct = (noise_count / total * 100) if total > 0 else 0
        print(f"eps={eps}, minpoints={minp} -> Clusters: {num_clusters}, Noise: {noise_count} ({noise_pct:.1f}%), Time: {(end_time - start_time)*1000:.1f}ms")

