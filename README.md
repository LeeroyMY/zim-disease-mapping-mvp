# ZimEpi Tracker 🌍🦠

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![PostGIS](https://img.shields.io/badge/PostGIS-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=Leaflet&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap_5-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white)

**ZimEpi Tracker** is a web-based geospatial and temporal infectious disease surveillance prototype developed for Zimbabwe. It is designed to modernize disease reporting, facilitate real-time spatial analytics, and ensure patient privacy through automated geomasking.

This repository contains the source code for the prototype, demonstrating a full-stack spatial architecture capable of handling national-scale line-list epidemiological data.

---

##  Key Features

### 1.  Role-Oriented Access & Workflows
*   **Custom Login Interface**: A dedicated, branded entry point separating clinical and administrative pathways.
*   **Health Personnel Dashboard**: A custom case management interface (CRUD) for reporting and managing individual disease records.
*   **Administrator Dashboard**: A high-level spatial analytics dashboard for national disease tracking.

### 2.  Advanced Geospatial Visualisation
*   **Point-Level Mapping**: High-performance rendering of thousands of individual case points using **Deck.GL** and **Leaflet**.
*   **Interactive Coordinate Capture**: Integrated **MapLibre** and **OpenLocationCode (Plus Codes)** in the reporting form to ensure highly accurate, standardized patient origin capture.
*   **Administrative Context**: Overlays of 101 province and district-level administrative boundaries.

### 3.  Spatial Analytics & Privacy
*   **Automated Donut Geomasking**: A privacy-preserving algorithm executed during API serialization. It automatically shifts true patient coordinates into an obscured radius (e.g., min 50m, max 500m) to protect identities while maintaining analytical validity.
*   **Backend Statistical Clustering**: Outbreak detection is offloaded directly to the database using **PostGIS `ST_ClusterDBSCAN`**, providing highly accurate, parameter-driven spatial clustering without burdening the browser memory.

### 4.  Dynamic Data Management
*   **Dynamic Schema Validation**: Supports the bulk ingestion of historical datasets (CSV/Excel) with dynamic column expansion to adapt to unpredictable data schemas.
*   **Real-time Temporal Filtering**: A highly responsive frontend dashboard enabling epidemiologists to instantly filter by disease, variant, severity, and date of onset.

---

## 🏗️ System Architecture

The project adheres to a four-layer technical architecture:

1.  **Presentation Layer**: HTML5, Bootstrap 5, Leaflet.js, Deck.GL (`map_logic.js`).
2.  **API/Application Layer**: Django, Django REST Framework.
3.  **Domain/Analytics Layer**: Custom Donut Geomasking algorithms, Spatial DBSCAN Clustering logic.
4.  **Data Layer**: PostgreSQL database extended with PostGIS for native spatial geometries (`BaseDiseaseCase`, `HealthFacility`, `AdministrativeBoundary`).

---

##  Setup & Installation

### Prerequisites
*   Python 3.10+
*   PostgreSQL 14+ with the **PostGIS** extension enabled
*   GDAL / GEOS libraries (required for GeoDjango)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/infectious-diseases-mapping.git
   cd infectious-diseases-mapping
   ```

2. **Create a virtual environment & install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure the Database**
   * Ensure PostgreSQL is running.
   * Create a database named `zim_disease_db`.
   * Enable the PostGIS extension in your database:
     ```sql
     CREATE EXTENSION postgis;
     ```
   * Update the `DATABASES` configuration in `core/settings.py` with your local PostgreSQL credentials.

4. **Apply Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Run the Development Server**
   ```bash
   python manage.py runserver
   ```

---

##  User Manual & Navigation Guide

### 1. Logging In
Navigate to `https://infectious-diseases-mapping.onrender.com` You be presented with the ZimEpi Tracker custom login interface. 
*   **Role Selection**: Click on either the **Administrator** or **Health Personnel** role cards. This will automatically populate the respective username and password for demonstration purposes.
*   **Automatic Routing**: After clicking "Sign In", the system evaluates your backend role permissions (`is_superuser`) and redirects you to the appropriate workspace.

### 2. Administrator Workflow (Spatial Dashboard)
If you log in as an Administrator, you are routed directly to the **Map Dashboard**.
*   **Map Interaction**: The map displays national disease points aggregated visually via Deck.GL. You can pan, zoom, and inspect dense areas without browser lag.
*   **Sidebar Filtering**: Click the hamburger menu on the left to open the filter sidebar. You can toggle specific diseases (e.g., Cholera, TB), filter by variants, and use the timeline slider to restrict data to specific date ranges.
*   **Spatial Outbreak Detection**: In the sidebar or toolbar, click the **Spatial Clustering** button. This triggers a backend PostGIS DBSCAN algorithm that groups dense outbreaks and returns the number of statistically significant clusters.
*   **Boundaries Layer**: Toggle the Administrative Boundaries switch to overlay the province and district-level polygons.

### 3. Health Personnel Workflow (Case Management)
If you log in as Health Personnel, you are routed to the **Case Management** interface (`/cases/manage/`). This dashboard is divided into three main tabs:

*   **Tab 1: Add New Case (Reporting)**
    *   Fill in demographic details (Disease Type, Age, Gender, Date of Onset).
    *   Select the **Reporting Health Facility** from the searchable dropdown list.
    *   **Geocoding Patient Origin**: Use the interactive MapLibre mini-map to pinpoint the exact residence of the patient. You can click on the map manually, use the address search bar, or use the "Pinpoint My Location" GPS button.
    *   Click "Save Case to Database". The system automatically generates the spatial coordinates and OpenLocationCode (Plus Code) for the database.
*   **Tab 2: My Reported Cases (Editing)**
    *   Provides a paginated, tabular list of all cases you have personally reported.
    *   Click the **Edit** button next to any record to update clinical statuses (e.g., Outcome, Severity).
*   **Tab 3: Global Database (Read-Only)**
    *   A high-level tabular view of the latest national cases submitted by all users. 
    *   Patient records are anonymized (displaying UUIDs instead of names) to maintain privacy.

---

##  Evaluation Metrics & Benchmarks

During simulated national-scale load testing, the prototype achieved the following benchmarks:
*   **Dataset Capacity**: Successfully rendered 8,898 simultaneous line-list case records alongside 101 high-resolution polygon boundaries.
*   **Clustering Performance**: Server-side PostGIS DBSCAN executed in an average of **107 milliseconds** (warm-cache) to analyze nearly 9,000 points.
*   **Payload Efficiency**: The JSON clustering response requires merely ~83 bytes of bandwidth, drastically reducing network bottlenecks compared to transferring raw geometries for client-side math.

---

##  Future Work
While the prototype successfully proves the technical viability of the framework, future phases would include:
*   Integration with national **DHIS2** APIs.
*   Implementation of production-level audit logging.
*   Hardened endpoint authorization for strict Role-Based Access Control (RBAC).

---
*Developed as a dissertation prototype for spatial epidemiological surveillance.*

