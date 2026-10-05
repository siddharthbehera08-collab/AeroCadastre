#!/usr/bin/env python3
"""
AeroCadastre SIH26012 — Runtime Environment Diagnostic Tool.
Audits installed Python version, key geospatial and ML packages, and system capability.
"""

import sys
import shutil


def check_env():
    print("=" * 70)
    print("AEROCADASTRE SIH26012 — RUNTIME ENVIRONMENT AUDIT")
    print("=" * 70)
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")

    packages = [
        ("torch", "PyTorch Deep Learning Engine"),
        ("rasterio", "GeoTIFF & GDAL Raster I/O"),
        ("geopandas", "Vector Geospatial Analysis"),
        ("shapely", "Computational Geometry & Topology"),
        ("numpy", "Numerical Array Processing"),
        ("fastapi", "Asynchronous REST API Framework"),
        ("pydantic", "Schema Validation"),
        ("psycopg2", "PostgreSQL Database Adapter"),
    ]

    all_ok = True
    for pkg, desc in packages:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "installed")
            print(f"[{'OK':<4}] {pkg:<12} (v{ver}) - {desc}")
        except ImportError:
            print(f"[{'MISSING':<7}] {pkg:<12} - {desc}")
            all_ok = False

    print("-" * 70)
    psql_bin = shutil.which("psql")
    print(f"PostgreSQL CLI (psql): {'FOUND (' + psql_bin + ')' if psql_bin else 'NOT IN PATH (Standalone In-Memory fallback active)'}")
    print("=" * 70)
    return all_ok


if __name__ == "__main__":
    check_env()
