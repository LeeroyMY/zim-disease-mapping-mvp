# ZimEpi Tracker Data Governance

## Data Provenance and Synthetic Nature

The dataset included in this repository (`data/synthetic/local_data_dump_synthetic.json`) and any other case data loaded by default is strictly **synthetic, anonymised, and/or public-derived data**. 

- No real patient records, names, national IDs, or identifiable medical data are included in this prototype.
- Coordinates provided in the synthetic data are simulated or perturbed using Donut Geomasking algorithms to preserve k-anonymity.
- This data is provided solely for the purpose of demonstrating the spatial clustering, temporal analytics, and geospatial capabilities of the platform.

## Ethics and Production Deployment

Deploying ZimEpi Tracker in a real clinical or public health setting requires:
1. Formal ethics approval and data-sharing agreements with the relevant Ministry of Health or governing body.
2. Secure, HIPAA/GDPR-compliant infrastructure and database hosting.
3. Proper configuration of Role-Based Access Control (RBAC) and disabled demo credentials.
4. An established protocol for managing spatial privacy.
