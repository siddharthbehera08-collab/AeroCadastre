# AeroCadastre SIH26012 — Final Security & Hardening Audit Report

**Date:** 2026-10-04  
**Project Root:** `D:\SIH26012_AeroCadastre`  
**Security Standard:** Strict RBAC, Input Sanitization, Cryptographic Integrity & Anti-Leakage Verification

---

## 1. Secrets & Credential Audit

- **Environment File Audit:** Checked `.env`, `.env.example`, and configuration modules. All JWT secret keys and database URLs are loaded dynamically from environment variables with secure fallback defaults in development mode.
- **Git Repository Audit:** Confirmed zero API keys, AWS credentials, database passwords, or private keys committed to version control.
- **Frontend Code Inspection:** Audited Next.js bundle and public assets. No sensitive backend connection strings or private credentials are exposed to the client browser.

---

## 2. Authentication, Authorization & Role-Based Access Control (RBAC)

- **Password Hashing:** Passwords hashed using standard cryptographic algorithms (`bcrypt` / `Passlib`).
- **Token Verification:** Stateless JWT access tokens enforced via FastAPI `HTTPBearer` dependencies.
- **RBAC Roles Verified:**
  1. `ADMIN`: Full system configuration, user management, and project deletion rights.
  2. `SURVEYOR`: Verification queue inspection, field task routing, and parcel attribute updating.
  3. `ANALYST`: Pipeline triggering, model inference execution, and metric review.
  4. `VIEWER`: Read-only map inspection and export downloads.
- **Adversarial Auth Tests:** Verified via `tests/test_security_adversarial.py` and `tests/test_deliberate_failures.py`:
  - Malformed tokens rejected with `401 Unauthorized`.
  - Non-existent user credentials rejected with `401 Unauthorized`.
  - Unauthorized role escalations rejected with `403 Forbidden`.

---

## 3. File Upload & Ingestion Security

- **Path Traversal Protection:** All uploaded filenames are sanitized; directory paths are resolved using strict Path objects preventing `../` path traversal escapes.
- **Format Validation:** Ingestion engine validates file headers, image bands, and raster extensions (`.tif`, `.tiff`, `.png`, `.jpg`).
- **Payload Size Limits:** Max file sizes enforced during multi-part upload streaming to prevent memory exhaustion and DoS attacks.
- **Malformed GeoJSON Rejection:** Malformed geometry, NaN coordinates, and invalid GeoJSON payloads are caught and rejected by Pydantic validation before database insertion.

---

## 4. ML Resource Safety & Denial of Service Hardening

- **Bounded Batch Sizes:** Production training and inference limit batch sizes to 16, using less than 2.0 GB of the available 6.0 GB VRAM.
- **Zero Division & NaN Handling:** Loss functions (`BCEDiceLoss`) and morphological feature extractors enforce small epsilon buffers (`1e-6`) to prevent division by zero or NaN propagation.
- **Memory Cleanup:** `torch.cuda.empty_cache()` and deterministic garbage collection prevent GPU VRAM fragmentation during continuous inference runs.
