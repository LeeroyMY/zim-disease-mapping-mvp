# DHIS2 Integration Technical Plan

This document sketches the proposed future architecture for integrating ZimEpi Tracker with DHIS2 (District Health Information Software 2). **Note: This is future work and not currently implemented.**

## Integration Architecture Flow

```text
[ DHIS2 Tracker / API ] <---(REST / OAuth2)---> [ ZimEpi Sync Engine (Celery/Redis) ] ---> [ PostGIS Database ]
```

## API Options & Authentication
- **Endpoint**: The integration will likely utilize the DHIS2 `api/tracker/events` or `api/tracker/trackedEntities` endpoints.
- **Authentication**: Service accounts utilizing OAuth2 or Personal Access Tokens (PATs). 

## Proposed Field Mapping

| DHIS2 Data Element / Attribute | ZimEpi Tracker Field | Transformation Logic |
| :--- | :--- | :--- |
| `orgUnit` | `facility` | Resolve orgUnit ID to ZimEpi `HealthFacility` via mapping table. |
| `eventDate` | `date_of_onset` | Direct ISO date parsing. |
| `attributeOptionCombo` | `disease_type` | Map DHIS2 disease categorisation codes to ZimEpi models. |
| `coordinate` | `location` | Parse to PostGIS `Point` geometry (SRID 4326). |
| Custom Attributes | `extra_data` | Store any unmapped fields in the generic JSONB `extra_data` column. |

## Sync Mechanics & Data Handling
- **Deduplication**: Use patient identifier hashes and event UIDs from DHIS2 to prevent duplicate ingestion.
- **Near-Real-Time Sync**: A scheduled CRON job (e.g., using Celery Beat) polling the DHIS2 API with `updatedAfter` parameters.
- **Governance**: Data pulled from DHIS2 must immediately undergo the Donut Geomasking pipeline before caching or exposing to the map.
