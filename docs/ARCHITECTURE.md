# Architecture Guide: Infectious Diseases Mapping System

## Overview
This document outlines the high-level architecture and design decisions for the Infectious Diseases Mapping System. It is intended to help developers understand *why* certain architectural choices were made and how to navigate the codebase.

## Core Technologies
*   **Backend**: Django (Python) - Chosen for its robust ORM, admin panel, and rapid development capabilities.
*   **Database**: PostgreSQL with PostGIS - Crucial for handling advanced spatial queries, distance calculations, and rendering spatial geometries.
*   **Frontend Map**: MapLibre GL JS - Chosen over Leaflet for its ability to handle massive vector tile datasets and render hundreds of thousands of raw points using WebGL, which is necessary for avoiding the Modifiable Areal Unit Problem (MAUP).
*   **Spatial Analysis**: Turf.js (Client-side) - Used for real-time spatial operations (like dynamic radius filtering and Kernel Density Estimation) without round-tripping to the server.

## Design Patterns & Key Decisions

### 1. Abstract Disease Models (`BaseDiseaseCase`)
**Why?** In epidemiological surveillance, many diseases share the same core reporting structure.
**How it works:**
*   `BaseDiseaseCase` is an abstract Django model containing fields universal to all cases (location, date of onset, patient demographics, facility).
*   Concrete models (like `CholeraCase`, `HIVCase`, `TBCase`) inherit from this base class.
*   *Constraint Note:* While the views are built with dynamic schema generation logic (scanning CSVs for extra columns), the system currently strictly enforces saving only to predefined models (Cholera, HIV, TB) to maintain data purity and prevent database bloat. This is enforced in `surveillance/utils.py`.

### 2. Spatial Analysis & MAUP Mitigation
**Why?** The Modifiable Areal Unit Problem (MAUP) occurs when point-based data is aggregated into arbitrary administrative boundaries (like districts or wards), skewing the visual representation of disease hotspots.
**How it works:**
*   **Raw Point Rendering**: Instead of aggregating data on the server, the server sends GeoJSON FeatureCollections of raw case coordinates. MapLibre renders these instantly using WebGL.
*   **Kernel Density Estimation (KDE)**: We use heatmaps based on raw points rather than choropleth maps of administrative regions. This provides a continuous surface of disease density independent of political borders.
*   **Spatial Indexing**: All models use PostGIS `GistIndex` on the `location` field to ensure that spatial queries (like finding the nearest health facility) remain performant even with millions of records.

### 3. Data Ingestion & Dataset Parsing
**Why?** Epidemiological datasets can be massive and come in varied formats (CSV, Excel, GeoJSON, or Newick phylogenetic trees).
**How it works:**
*   The `upload_dataset` view parses files dynamically.
*   **Phase 1 (Pre-flight):** Scans the file to detect new columns and validates mandatory fields (latitude/longitude).
*   **Phase 2 (Schema Update):** Creates or updates the dynamic model schema to accommodate any newly discovered columns.
*   **Phase 3 (Bulk Insert):** Uses Django's `bulk_create` for performance.
*   **Optimization**: During upload, we use an in-memory spatial caching dictionary (`facility_cache = {}`) mapped by coordinate tuples `(lon, lat)` to avoid redundant PostGIS distance queries when assigning cases from identical coordinates to the nearest health facility.

## Data Flow
1.  **Case Reporting**: A health worker submits a case via the frontend form. The backend determines the disease model, creates missing facilities using PostGIS, and saves the case.
2.  **Visualization**: The frontend requests `/api/cases/latest`. The backend queries all subclasses of `BaseDiseaseCase` and serializes them into a unified GeoJSON FeatureCollection. MapLibre consumes this and seamlessly updates the map layers.
