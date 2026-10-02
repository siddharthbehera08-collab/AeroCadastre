# SIH26012 AeroCadastre — Security & Authorization Review (`SECURITY_REVIEW.md`)

**Date:** 2026-10-01  
**Scope:** Authentication, Role-Based Access Control (`RBAC`), SQL Injection, Path Traversal, Upload Sanitization, Secrets Management

---

## 1. Security Controls Implemented & Verified

| Security Domain | Implementation Details | Adversarial Test Verification (`test_02`, `test_13`, `test_20`) | Status |
|---|---|---|---|
| **Password Hashing** | PBKDF2-HMAC-SHA256 (`200,000` iterations, cryptographic random 16-byte salt, `hmac.compare_digest` constant-time comparison) in `backend/app/core/security.py` | Verified password hashing & constant-time verification for `admin`, `surveyor`, `viewer` | `VERIFIED` |
| **JWT Authentication** | Pure-Python HMAC-SHA256 (`HS256`) signed tokens with `sub`, `role`, `iat`, `exp` claims (`backend/app/core/security.py`) | Forged signatures, tampered payloads, and expired tokens return `401 Unauthorized` | `VERIFIED` |
| **Role-Based Access Control (`RBAC`)** | `get_optional_user` + `assert_operator_can_mutate` enforces role checks across JWT Bearer token, `X-Operator-Role` header, and `operator_id` | `VIEWER` / `DEMO_USER` (`SIH26012_Reviewer`) receives `403 Forbidden` on `POST/PUT/DELETE /api/parcels`, `split`, `merge`, `POST/DELETE /api/projects`, and `POST/PUT /api/verification` | `VERIFIED` |
| **SQL Injection Protection** | All SQL and PostGIS spatial queries use SQLAlchemy 2.0 ORM bound parameters (`:pid`, `:wkt`, `:srid`) | Tested `' OR 1=1 --` and stacked query injection payloads; zero SQL injection vulnerability | `VERIFIED` |
| **Path Traversal Protection** | `GET /api/exports/download` resolves `.resolve()` and enforces strict directory containment within `settings.outputs_dir` / `settings.PROJECT_ROOT`; `POST /api/upload` strips directory prefixes via `Path(file.filename).name` | Tested `?file_path=../../backend/app/main.py` and `../../../Windows/win.ini` $\rightarrow$ blocked with `403 Forbidden` | `VERIFIED` |
| **File Upload Sanitization** | `POST /api/upload` whitelists geospatial extensions (`.geojson`, `.json`, `.gpkg`, `.zip`, `.shp`, `.tif`, `.tiff`, `.csv`, `.kml`) and enforces size limits (`50 MB`) | Uploaded `.exe` and `.sh` payloads $\rightarrow$ rejected with `400 Bad Request` | `VERIFIED` |
| **Secrets & Configuration** | Loaded from environment variables / `.env` via `pydantic-settings` (`backend/app/core/config.py`) with `.env.example` template | Zero hardcoded production secrets in frontend bundle | `VERIFIED` |
| **Audit Trail Immutability** | Every state mutation writes an `AuditLog` record with `actor`, `operation`, `target_id`, `old_value_json`, `new_value_json`, and UTC timestamp | Verified across all project, parcel, verification, analysis, and export mutations | `VERIFIED` |
