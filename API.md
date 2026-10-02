# SIH26012 — AeroCadastre: REST API Reference (`API.md`)

Base URL: `http://127.0.0.1:8000`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | System, database, and storage health check |
| `GET` | `/api/dashboard` | Real project telemetry & counts for active scene |
| `GET` | `/api/projects` | List cadastral survey projects |
| `POST` | `/api/projects` | Create new cadastral survey project |
| `GET` | `/api/datasets` | List registered datasets |
| `POST` | `/api/upload` | Upload & validate GeoTIFF, PNG, GeoJSON, Shapefile, or CSV |
| `GET` | `/api/scenes` | List available synthetic & temporal scenes |
| `GET` | `/api/scenes/{scene_id}/rgb.png` | Serve scene drone RGB ortho image |
| `GET` | `/api/scenes/{scene_id}/bundle` | Fetch full multi-layer Web-GIS feature bundle |
| `POST` | `/api/pipeline/run` | Execute 24-step GeoAI inference, topology, and Council pipeline |
| `GET` | `/api/parcels` | List candidate or reference parcels |
| `POST` | `/api/parcels` | Create new parcel polygon in PostGIS |
| `PUT` | `/api/parcels/{parcel_id}` | Edit parcel geometry/vertices, land-use, or verification status |
| `POST` | `/api/parcels/{parcel_id}/split` | Subdivide parcel polygon into two valid sub-parcels |
| `POST` | `/api/parcels/merge` | Merge two parcels into a single verified polygon |
| `DELETE` | `/api/parcels/{parcel_id}` | Delete/reject candidate parcel |
| `POST` | `/api/verification/{parcel_id}` | Mark parcel `HUMAN_VERIFIED`, `REJECTED`, or `FIELD_VISIT_REQUESTED` |
| `GET` | `/api/history/{feature_id}` | Retrieve Parcel Time Machine version history (`T0`, `T1`, `T2`, `HUMAN_EDIT`) |
| `GET` | `/api/experiments` | List all trained ML experiments & metrics |
| `POST` | `/api/experiments/train` | Trigger live model training run |
| `POST` | `/api/copilot/query` | Query the deterministic tool-backed Cadastral AI Copilot |
| `POST` | `/api/exports` | Export & validate `GeoJSON`, `Shapefile`, `CSV`, or `GeoPackage` |
| `GET` | `/api/exports/download` | Download validated GIS export file |
| `GET` | `/api/audit-logs` | Retrieve traceable audit logs |
| `GET` | `/api/feedback` | Retrieve human-in-the-loop retraining feedback records |
