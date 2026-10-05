# AeroCadastre — Render Backend Deployment Guide

This guide details how to deploy the AeroCadastre GeoAI FastAPI backend onto **Render** using Docker.

---

## 1. Architecture Overview

```
                      +-----------------------------+
                      |   Render Web Service        |
                      |   (Docker: Python 3.12-slim)|
                      |                             |
                      |   FastAPI + Uvicorn         |
                      |   Port: ${PORT} (Dynamic)   |
                      +--------------+--------------+
                                     |
              +----------------------+----------------------+
              |                                             |
+-------------v---------------+              +--------------v--------------+
|  Render PostgreSQL + PostGIS |              |  Next.js Frontend (Vercel   |
|  (postgis & postgis_topology|              |  or Render Static Site)     |
|   extensions enabled)       |              |  NEXT_PUBLIC_API_URL        |
+-----------------------------+              +-----------------------------+
```

* **Entrypoint**: `backend.main:app` (aliased from `backend.app.main:app`).
* **Framework**: FastAPI, Uvicorn, SQLAlchemy 2.0, GeoAlchemy2, PostGIS, PyTorch (CPU).
* **Base Image**: `python:3.12-slim-bookworm` with Debian GIS libraries (`libgdal-dev`, `libgeos-dev`, `libproj-dev`, `libpq-dev`).

---

## 2. Render Web Service Settings

When creating a new Web Service in the [Render Dashboard](https://dashboard.render.com):

| Setting | Value |
|---|---|
| **Service Type** | Web Service |
| **Language / Runtime** | Docker |
| **Repository** | `https://github.com/siddharthbehera08-collab/AeroCadastre` |
| **Branch** | `master` |
| **Root Directory** | *(leave blank / default)* |
| **Dockerfile Path** | `./Dockerfile` |
| **Instance Type** | Free (0.1 CPU, 512 MB RAM) or Starter (0.5 CPU, 512 MB+) |
| **Health Check Path** | `/api/health` |
| **Auto-Deploy** | Yes |

---

## 3. Required Environment Variables on Render

In the **Environment** tab of your Render Web Service, configure the following variables:

| Variable Name | Required | Example / Description |
|---|---|---|
| `ENVIRONMENT` | Yes | `production` |
| `PORT` | Auto | Render sets this dynamically (defaults to `8000`). Dockerfile listens on `0.0.0.0:${PORT}`. |
| `DATABASE_URL` | Yes | Your Render PostgreSQL Internal Connection String. Example: `postgresql+psycopg2://user:pass@dpg-xxx:5432/aerocadastre_db` (Any `postgres://` prefix is automatically normalized). |
| `SECRET_KEY` | Yes | Secure 64-character hex key (e.g., generated with `openssl rand -hex 32`). |
| `JWT_ALGORITHM` | Optional | `HS256` (default) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional | `480` (default) |
| `CORS_ORIGINS` | Optional | `*` or comma-separated list of allowed origins (e.g. `https://your-frontend.vercel.app`). |
| `DEFAULT_GEOGRAPHIC_CRS` | Optional | `EPSG:4326` (default) |
| `DEFAULT_PROJECTED_CRS` | Optional | `EPSG:32643` (default UTM Zone 43N) |

> [!CAUTION]
> **Never commit production `SECRET_KEY` or `DATABASE_URL` into git repository or Dockerfile.** Always provide them via Render Environment Variables.

---

## 4. PostgreSQL + PostGIS Database Setup on Render

1. Create a **PostgreSQL Database** on Render.
2. In the Render PostgreSQL dashboard, connect to the database via `psql` or the web shell and verify/create PostGIS extensions:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   CREATE EXTENSION IF NOT EXISTS postgis_topology;
   ```
3. Copy the **Internal Database URL** from the database settings page.
4. Add it as the `DATABASE_URL` environment variable in your Web Service.

---

## 5. Database Migrations & Alembic

The FastAPI backend automatically ensures the schema on startup via its application lifespan (`init_postgis_schema()` and `ensure_demo_seed_data()`).

If you prefer to execute migrations explicitly during deployment:
```bash
alembic upgrade head
```

---

## 6. Health Check Verification

The service exposes the primary health endpoint at:
```http
GET /api/health
```

Expected JSON response:
```json
{
  "status": "ONLINE",
  "project": "SIH26012_AeroCadastre",
  "database_engine": "PostgreSQL + PostGIS",
  "postgresql_version": "PostgreSQL 16.x...",
  "postgis_version": "3.x...",
  "public_table_count": 24,
  "data_label": "SYNTHETIC DEMO DATA",
  "legal_disclaimer": "PRELIMINARY / CANDIDATE GEOMETRY - NOT LEGALLY AUTHORITATIVE LAND RECORDS",
  "parcels_in_db": 100,
  "experiments_in_db": 11,
  "table_counts": { ... }
}
```

*If the database is temporarily unreachable, `/api/health` gracefully returns status `DEGRADED` rather than crashing.*

---

## 7. Render Free Tier (512 MB RAM) Characteristics & Scaling

- **RAM Constraint**: The Render Free tier provides 512 MB of RAM. Light PyTorch inference models (`MicroUNet`, `MicroResUNet`) are loaded lazily on CPU.
- **Spin-down**: Free services spin down after 15 minutes of inactivity. The initial wake-up request may take ~30–50 seconds.
- **Scaling Up**: For continuous zero-latency operation and high-throughput multi-user inference on large aerial orthomosaics, upgrade the instance to Render **Starter** or **Standard** tier.

---

## 8. Frontend Compatibility

When deploying the Next.js frontend (e.g. to Vercel or Render):
- Set `NEXT_PUBLIC_API_URL` to your Render backend URL (e.g., `https://aerocadastre-backend.onrender.com`).
- The frontend will automatically route all WebGIS editing, AI parcelling, and surveyor verification requests to the Render backend.
