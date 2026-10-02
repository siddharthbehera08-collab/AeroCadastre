# SIH26012 AeroCadastre — Postman Collection Setup & Manual Testing Guide

## 1. Collection File Location

The complete Postman v2.1 collection is located at:

```text
D:\SIH26012_AeroCadastre\AeroCadastre_Backend.postman_collection.json
```

---

## 2. Importing into Postman

1. Open **Postman Desktop** or **Postman Web**.
2. Click **Import** in the top-left workspace bar.
3. Drag and drop `D:\SIH26012_AeroCadastre\AeroCadastre_Backend.postman_collection.json`.
4. Ensure the FastAPI backend is running on `http://127.0.0.1:8000`:
   ```powershell
   python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
   ```

---

## 3. Collection Variables

The collection pre-configures the following variables (automatically updated by test scripts during a Collection Run):

| Variable | Default Value | Description |
|---|---|---|
| `baseUrl` | `http://127.0.0.1:8000` | FastAPI backend base URL |
| `accessToken` | *(auto-populated)* | Populated by `POST /api/auth/login` |
| `projectId` | `PROJ_SIH26012_DEMO` | Default seeded cadastral project ID |
| `createdProjectId` | *(auto-populated)* | Populated by `POST /api/projects` |
| `parcelId` | `scene_urban_T1_PARCEL_001` | Default seeded candidate parcel ID |
| `createdParcelId` | *(auto-populated)* | Populated by `POST /api/parcels` |
| `verificationId` | *(auto-populated)* | Populated by `POST /api/verification` |
| `analysisId` | *(auto-populated)* | Populated by `POST /api/analysis/run` |

---

## 4. Request Folders Included

1. **1. Health & PostGIS Diagnostics**
   - `GET /api/health` — Verifies PostgreSQL 16.4 + PostGIS 3.6.2 connectivity and table counts.
2. **2. Authentication & Security**
   - `POST /api/auth/login (Valid Credentials)` — Logs in as `surveyor@aerocadastre.gov.in` and stores `{{accessToken}}`.
   - `GET /api/auth/me (Authorized)` — Verifies Bearer JWT authentication.
   - `GET /api/auth/me (Unauthorized - 401)` — Verifies missing token rejection.
3. **3. Projects CRUD**
   - `GET /api/projects`, `POST /api/projects`, `GET /api/projects/{id}`, `PUT /api/projects/{id}`, `DELETE /api/projects/{id}`, and `GET /api/projects/non-existent-project-id (404)`.
4. **4. Parcels CRUD & GeoJSON**
   - `GET /api/projects/{project_id}/parcels`, `GET /api/parcels/{id}`, `POST /api/parcels`, `PUT /api/parcels/{id}`, `DELETE /api/parcels/{id}`, and `POST /api/parcels (Malformed Geometry - 400/422)`.
5. **5. Buildings & Roads**
   - `GET /api/parcels/{parcel_id}/buildings` and `GET /api/projects/{project_id}/roads`.
6. **6. Verification Workflow**
   - `GET /api/verification/queue`, `POST /api/verification`, and `PUT /api/verification/{id}`.
7. **7. GIS Topology & Conflict Analysis**
   - `GET /api/parcels/{id}/topology` and `GET /api/parcels/{id}/conflicts`.
8. **8. AI Analysis & Inference Persistence**
   - `POST /api/analysis/run` and `GET /api/analysis/{id}`.
9. **9. AI Council Deliberation**
   - `POST /api/council/analyze` and `GET /api/council/{parcel_id}`.
10. **10. Cadastral Exports**
    - `POST /api/exports (GeoJSON)`.
