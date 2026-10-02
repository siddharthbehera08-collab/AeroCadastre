# SIH26012 AeroCadastre — Adversarial & Torture Test Report (`ADVERSARIAL_TEST_REPORT.md`)

**Date:** 2026-10-01  
**Test Suite:** `backend/tests/test_full_system_adversarial.py`  
**Result:** All adversarial test cases passed (`100%` expected rejection / recovery behavior; zero unhandled `500` crashes).

---

## 1. Summary of Adversarial Attack Vectors Tested

We systematically attempted to break every layer of AeroCadastre using malformed inputs, geometric torture polygons, corrupted ML tensors, unauthorized role escalation, path traversal payloads, and mid-transaction database failures.

| Category | Adversarial Vector | Target Endpoint / Service | Expected Behavior | Observed Result | Status |
|---|---|---|---|---|---|
| **Auth & RBAC** | Missing Bearer token on `/api/auth/me` | `GET /api/auth/me` | `401 Unauthorized` | `401 Unauthorized` | `PASS` |
| **Auth & RBAC** | Forged / tampered HS256 JWT token | `GET /api/auth/me`, `POST /api/parcels` | `401 Unauthorized` (`Invalid or expired token`) | `401 Unauthorized` | `PASS` |
| **Auth & RBAC** | `VIEWER` role (`viewer` JWT or `X-Operator-Role: VIEWER` or `SIH26012_Reviewer`) attempting parcel create/edit/split/merge/delete | `POST/PUT/DELETE /api/parcels`, `POST /api/verification/{id}` | `403 Forbidden` | `403 Forbidden` | `PASS` |
| **Auth & RBAC** | SQL Injection payload in login username (`' OR 1=1 --`) | `POST /api/auth/token` | `401 Unauthorized` (parameterized SQLAlchemy query) | `401 Unauthorized` | `PASS` |
| **Geometry Torture** | Bowtie self-intersecting polygon (`[(0,0),(2,2),(0,2),(2,0),(0,0)]`) | `POST /api/parcels`, `PUT /api/parcels/{id}` | Detected (`is_valid=False`) and repaired via `ST_MakeValid` + `validate_and_repair_polygon`, or rejected if degenerate | Repaired (`REPAIRED_SELF_INTERSECTION`) & persisted valid `POLYGON` | `PASS` |
| **Geometry Torture** | Fewer than 3 vertices (`[[77.59, 12.97], [77.591, 12.971]]`) | `POST /api/parcels`, `PUT /api/parcels/{id}` | `400/422` validation error | `422 Unprocessable Entity` | `PASS` |
| **Geometry Torture** | Zero-area collinear spike polygon | `POST /api/parcels`, `PUT /api/parcels/{id}` | Rejected (`area_sqm < 1.0` m²) | `400/422` Rejected | `PASS` |
| **Geometry Torture** | Sub-square-meter micro-polygon (`0.01` m²) | `POST /api/parcels`, `PUT /api/parcels/{id}` | Rejected (`Parcel area too small (< 1.0 sqm)`) | `400 Bad Request` | `PASS` |
| **Geometry Torture** | Continental-scale polygon (`> 5,000,000` m²) | `POST /api/parcels`, `PUT /api/parcels/{id}` | Rejected (`Parcel area exceeds maximum allowed cadastral limit`) | `400 Bad Request` | `PASS` |
| **Geometry Torture** | Out-of-bounds geographic coordinates (`lon=240.0, lat=95.0`) | `POST /api/parcels` | Rejected (`422` coordinate range violation) | `422 Unprocessable Entity` | `PASS` |
| **Split / Merge** | Extreme split ratio (`0.01`, `0.99`, `-0.5`, `1.5`) | `POST /api/parcels/{id}/split` | Rejected (`422` Pydantic range check `[0.15, 0.85]`) | `422 Unprocessable Entity` | `PASS` |
| **Split / Merge** | Invalid split axis (`DIAGONAL`) | `POST /api/parcels/{id}/split` | Rejected (`400` invalid axis) | `400 Bad Request` | `PASS` |
| **Split / Merge** | Merging a parcel with itself (`[P1, P1]`) | `POST /api/parcels/merge` | Rejected (`Cannot merge a parcel with itself`) | `400 Bad Request` | `PASS` |
| **Split / Merge** | Merging two disjoint non-touching parcels (`1 km` apart) | `POST /api/parcels/merge` | Rejected (`Merged geometry is a MultiPolygon; parcels must share a boundary`) | `400 Bad Request` | `PASS` |
| **ML Pipeline** | Nonexistent image file path | `GeoAIInferenceEngine.predict_tile_from_path` | Raises `FileNotFoundError` cleanly | `FileNotFoundError` | `PASS` |
| **ML Pipeline** | Empty (`0x0`) numpy array or 2D grayscale array (missing channels) | `GeoAIInferenceEngine.predict_tile` | Raises `ValueError` with descriptive message | `ValueError` | `PASS` |
| **ML Pipeline** | Wrong channel count (`2` channels or `5` channels) | `GeoAIInferenceEngine.predict_tile` | Raises `ValueError` | `ValueError` | `PASS` |
| **ML Pipeline** | `NaN` / `Inf` pixel values in input imagery | `GeoAIInferenceEngine.predict_tile` | Raises `ValueError("Input image contains NaN or Inf values")` | `ValueError` | `PASS` |
| **ML Pipeline** | Extreme tiny (`8x8`) or huge (`8192x8192`) tile dimensions | `GeoAIInferenceEngine.predict_tile` | Raises `ValueError` (`Tile dimensions must be between 16 and 4096`) | `ValueError` | `PASS` |
| **ML Pipeline** | All-black (`zeros`) and all-white (`255`) tiles | `GeoAIInferenceEngine.predict_tile` | Executes without `NaN` probabilities; probabilities remain in `[0.0, 1.0]` | Clean output dict | `PASS` |
| **Copilot** | Empty or whitespace-only query (`"   "`) | `POST /api/copilot/ask` | `400/422` error | `422 Unprocessable Entity` | `PASS` |
| **Copilot** | Query referencing nonexistent parcel (`P_999`) or nonexistent project | `POST /api/copilot/ask` | Explicitly reports parcel/project not found in PostgreSQL (zero hallucination) | Explicit not-found response | `PASS` |
| **Uploads & Exports** | Uploading `.exe` / `.sh` malicious script or corrupt `.geojson` | `POST /api/upload` | Rejected (`400 Bad Request`) or quarantined with `INVALID` validation status | `400` / `INVALID` status | `PASS` |
| **Uploads & Exports** | Path traversal on export download (`?file_path=../../backend/app/main.py`) | `GET /api/exports/download` | Blocked (`403 Forbidden: Access outside outputs directory is forbidden`) | `403 Forbidden` | `PASS` |
| **DB Transactions** | Mid-transaction failure during parcel creation | SQLAlchemy `Session` rollback test | Full rollback; zero orphaned `Parcel` or `AuditLog` rows left in PostgreSQL | Verified `0` partial rows | `PASS` |
