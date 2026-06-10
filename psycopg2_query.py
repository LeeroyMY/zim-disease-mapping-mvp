import psycopg2
import time

conn = psycopg2.connect(dbname='zim_disease_db', user='postgres', password='Maturure00398@', host='localhost')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM surveillance_healthfacility;')
facilities_count = cursor.fetchone()[0]

query = """
    WITH clustered AS (
        SELECT ST_ClusterDBSCAN(location::geometry, 0.045, 3) OVER() AS cluster_id
        FROM (
            SELECT location FROM surveillance_choleracase WHERE location IS NOT NULL
            UNION ALL
            SELECT location FROM surveillance_hivcase WHERE location IS NOT NULL
            UNION ALL
            SELECT location FROM surveillance_tbcase WHERE location IS NOT NULL
            UNION ALL
            SELECT location FROM surveillance_malariacase WHERE location IS NOT NULL
            UNION ALL
            SELECT location FROM surveillance_typhoidcase WHERE location IS NOT NULL
        ) all_cases
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
    cursor.execute(query)
    result = cursor.fetchone()
    end = time.time()
    times.append(int((end - start) * 1000))

print('Health Facilities:', facilities_count)
print('Results:', result)
print('Times:', times)
