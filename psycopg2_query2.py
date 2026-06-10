import psycopg2

conn = psycopg2.connect(dbname='zim_disease_db', user='postgres', password='Maturure00398@', host='localhost')
cursor = conn.cursor()

# Get province and district counts
cursor.execute("""
    SELECT level, COUNT(*) 
    FROM surveillance_administrativeboundary 
    GROUP BY level;
""")
boundary_counts = cursor.fetchall()
print('Boundaries:', boundary_counts)

# Get the centroid of the largest cluster
query = """
    WITH clustered AS (
        SELECT location::geometry as geom, ST_ClusterDBSCAN(location::geometry, 0.045, 3) OVER() AS cluster_id
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
    ),
    cluster_sizes AS (
        SELECT cluster_id, COUNT(*) as size, ST_Centroid(ST_Collect(geom)) as centroid
        FROM clustered
        WHERE cluster_id IS NOT NULL
        GROUP BY cluster_id
    )
    SELECT cluster_id, size, ST_Y(centroid) as lat, ST_X(centroid) as lon
    FROM cluster_sizes
    ORDER BY size DESC
    LIMIT 1;
"""
cursor.execute(query)
largest = cursor.fetchone()
print('Largest cluster:', largest)
