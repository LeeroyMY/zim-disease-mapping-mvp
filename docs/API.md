# ZimEpi Tracker API Documentation

This lightweight API documentation outlines the core endpoints available in the system. 

## Base URL
`/api/`

## Authentication
All write operations and sensitive endpoints require authentication via Session or Token (depending on deployment). Ensure CSRF tokens are passed correctly for browser-based requests.

## Endpoints

### 1. `GET /api/cases/`
Retrieves a unified GeoJSON FeatureCollection of all diseases for map rendering.
- **Notes**: HIV cases are intentionally excluded from point-level mapping feeds for privacy reasons. Donut geomasking is applied to coordinates.

### 2. `GET /api/boundaries/?tolerance=0.01`
Retrieves administrative boundaries (provinces, districts).
- **Parameters**: 
  - `tolerance` (float): Optional. Simplifies the geometry using PostGIS ST_SimplifyPreserveTopology. Recommended: `0.01` for national views to vastly reduce payload size.

### 3. `GET /api/latest-cases/?since=<timestamp>`
Polls for new cases created since the specified ISO timestamp.
- **Parameters**: `since` (string, ISO format).

### 4. `POST /api/spatial-clustering/`
Executes DBSCAN spatial clustering on the database level.
- **Body Requirement**: JSON object containing an array of points and diseases.
```json
{
  "points": [{"lat": -19.0, "lon": 29.0, "date": "2024-01-01"}],
  "diseases": ["cholera"]
}
```
- **Returns**: Clustering statistics (clustered_count, noise_count, num_clusters).
- **Errors**: Returns 400 Bad Request if points are insufficient or if the disease is HIV (distance-based clustering is blocked for HIV).
