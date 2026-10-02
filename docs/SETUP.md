# SIH26012 — AeroCadastre: Setup & Execution Guide

## 1. Storage & Environment Configuration

All project files, datasets, models, databases, exports, and package caches reside on `D:\SIH26012_AeroCadastre\`.

Copy `.env.example` to `.env` if you wish to connect to an external PostgreSQL + PostGIS instance:
```ini
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/aerocadastre
```
By default, if no external PostgreSQL daemon is running on port 5432, the platform automatically uses the embedded PostGIS-compatible spatial database at `D:\SIH26012_AeroCadastre\database\aerocadastre_postgis.db` with `ST_*` spatial SQL functions (`ST_Area`, `ST_Perimeter`, `ST_IsValid`, `ST_MakeValid`, `ST_Intersects`, `ST_Overlaps`, `ST_Distance`, `ST_SRID`, `ST_AsGeoJSON`) backed by Shapely 2.1 and PyProj 3.8 (`EPSG:4326` / `EPSG:32643`).

To initialize a standalone PostgreSQL + PostGIS server with the full DDL:
```bash
psql -U postgres -d aerocadastre -f D:\SIH26012_AeroCadastre\database\postgis_schema.sql
```

## 2. Generating Synthetic Data & Training Models

```powershell
cd D:\SIH26012_AeroCadastre
python -m synthetic_data.generator
python -m backend.ml.trainer
```

## 3. Running Backend & Frontend

```powershell
# Terminal 1: FastAPI Backend (Port 8000)
cd D:\SIH26012_AeroCadastre
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Next.js Web-GIS Frontend (Port 3000)
cd D:\SIH26012_AeroCadastre\frontend
npm run dev
```
