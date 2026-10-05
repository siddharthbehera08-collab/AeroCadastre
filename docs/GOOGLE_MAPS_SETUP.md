# Google Maps JavaScript API Configuration Guide

## Overview

AeroCadastre integrates the Google Maps JavaScript API to provide satellite basemap imagery for context while overlaying sovereign GeoAI cadastral layers (administrative boundaries, inferred candidate parcels, building footprints, and road corridors).

---

## 1. Environment Variable Setup

In the frontend directory (`frontend/`):

1. Create or open `.env.local`:
   ```bash
   cp .env.example .env.local
   ```
2. Set your Google Maps JavaScript API Key:
   ```env
   NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=YOUR_ACTUAL_API_KEY_HERE
   NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
   ```

> [!IMPORTANT]
> **Zero Key Leakage Policy:**
> Never commit `.env.local` or any hardcoded API keys into git. `.env.local` is included in `.gitignore`.

---

## 2. Graceful Fallback Mode

If `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` is not provided:
- The system automatically displays a clear, informative status pill on the WebGIS canvas:
  ```
  Google Satellite: Not configured (NEXT_PUBLIC_GOOGLE_MAPS_API_KEY unset) — Operating in Sovereign WebGIS Mode
  ```
- The WebGIS canvas continues to function with full interactive capabilities (pan, zoom, vertex editing, polygon drawing, metric distance measurement, parcel split/merge, and multi-layer toggling).
- No blank screens or JavaScript errors are generated.

---

## 3. Required Google Cloud API Permissions

When configuring your key in Google Cloud Console:
1. Enable **Maps JavaScript API**.
2. Restrict HTTP referrers to:
   - `http://localhost:3000/*`
   - `http://127.0.0.1:3000/*`
3. Optional: Enable **Geocoding API** for location search.

---

## 4. Layer Integration Hierarchy

When Google Satellite is active, the following AeroCadastre GIS layers render over the basemap:
1. **Basemap:** Google Satellite Tile Service (or Sovereign WebGIS Canvas Fallback)
2. **Administrative Boundaries:** Maharashtra State → Pune District → Taluks (Pune City, Haveli, Mulshi, Khed with HQs)
3. **AI Preliminary Parcels:** Colored by multi-agent confidence or verified land use class
4. **Building Evidence:** Inferred footprints with frozen GPU ResUNet checkpoint scores
5. **Road Evidence:** Road centerlines and buffered access corridors
6. **Topology Issues & Conflicts:** Highlighted slivers, overlaps, and access anomalies
7. **AI Council Deliberation:** 6-agent voting summary and ground verification routing
