# AeroCadastre Operational Runbook
SIH26012 — End-to-End System Operation & Maintenance

## Quick Start (One Command)

To verify the database, model checkpoints, seed data, and launch both backend and frontend:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_all.ps1
```

To run pre-flight environment checks only without launching web servers:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_all.ps1 -CheckOnly
```

---

## Service Endpoints & Ports

| Service | Port / URI | Description |
| :--- | :--- | :--- |
| **Next.js WebGIS** | `http://localhost:3000` | Interactive WebGIS interface with parcel editing |
| **FastAPI Backend** | `http://127.0.0.1:8000` | REST API core |
| **Interactive API Docs**| `http://127.0.0.1:8000/docs` | Swagger OpenAPI specification |
| **System Health** | `http://127.0.0.1:8000/api/health` | Service uptime and compliance notice |
| **Admin Boundaries** | `http://127.0.0.1:8000/api/gis/admin-boundaries` | Maharashtra State -> District -> Taluk GeoJSON |
| **Pune Pilot Layers**| `http://127.0.0.1:8000/api/gis/pune-pilot` | Authentic Pune vector evidence & GPU champions |
| **PostgreSQL / PostGIS**| `127.0.0.1:5432` | Database `aerocadastre`, user `postgres` |

---

## Database Management

PostgreSQL runs from `D:\PostgreSQL\data`.

- **Check status:**
  ```powershell
  python database/manage_postgres.py status
  ```
- **Start server (non-blocking):**
  ```powershell
  python database/manage_postgres.py start
  ```
- **Stop server:**
  ```powershell
  python database/manage_postgres.py stop
  ```

---

## Running Verification & Demos

1. **Run Authentic Indian Pune Pilot Demo:**
   ```powershell
   python scripts/run_indian_pune_demo.py
   ```

2. **Run Full Regression Test Suite:**
   ```powershell
   python -m pytest tests/ -q
   ```
   *Expected result: 140 passed, 3 skipped in ~20s.*

3. **Build Frontend:**
   ```powershell
   cd frontend
   npm run build
   ```
