# AeroCadastre SIH26012 — Dataset Provenance & Data Usage Contracts
**Status Date:** 2026-10-04  
**Primary Principle:** Zero Fabrication, Strict Provenance Auditing, Ethical Licensing  

---

## 1. Dataset Register & Status Overview

| Dataset Name | Source / Provider | Geographic Coverage | Intended Purpose | AeroCadastre Classification | License / Terms |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Inria Aerial Image Labeling** | INRIA | Europe & USA (5 cities) | Building footprint segmentation benchmark | **BENCHMARK_TRAINING_ONLY** | Non-commercial research |
| **SpaceNet 3 (Paris)** | SpaceNet / Maxar | Paris, France | Road network extraction benchmark | **BENCHMARK_TRAINING_ONLY** | CC BY-SA 4.0 |
| **World Bank Mumbai LULC** | World Bank / ESA EO4SD | Mumbai metropolitan area | Urban land-cover classification experiment | **SUPPLEMENTARY_EXPERIMENT** (89.26 km disjoint from Pune) | Open Data Commons |
| **Pune DEM (SRTM/Cartosat)** | NASA / ISRO NRSC | Pune study area (EPSG:32643) | Physical elevation and slope gradient extraction | **REAL_OPERATIONAL_EVIDENCE** | Public Domain / Open Government |
| **Pune OpenStreetMap Buildings** | OpenStreetMap contributors | Pune study area (EPSG:32643) | Auxiliary geometric reference cues | **WEAK_LABEL_REFERENCE_ONLY** | ODbL 1.0 |
| **Pune OpenStreetMap Roads** | OpenStreetMap contributors | Pune study area (EPSG:32643) | Auxiliary centerline corridor cues | **WEAK_LABEL_REFERENCE_ONLY** | ODbL 1.0 |
| **Pune High-Resolution Optical Imagery** | Indian Remote Sensing / Aerial | Pune study area | Primary visual evidence for building/road inference | **MISSING / HARD_BLOCKER** | Requires authorized statutory license |

---

## 2. Hard Blocker Statement: Optical Imagery

```
STATUS: BLOCKED_BY_IMAGERY_DATA
SEVERITY: CRITICAL
AFFECTED TARGETS: Model A (Pune), Model B (Pune), Model E (Pune), Model F (Pune)
DEPENDENCY: Sub-meter cloud-free optical orthoimagery for Pune bounding box [377550, 2047000, 380750, 2049200] (EPSG:32643).

ETHICAL & SCIENTIFIC COMMITMENT:
- We DO NOT use Sentinel-2 (10m) or Landsat (30m) as pseudo-cadastral imagery.
- We DO NOT scrape Google/Bing/ESRI tiles.
- We DO NOT fabricate artificial satellite imagery and present it as real Pune data.
- DOWNSTREAM REAL-DATA INFERENCE REMAINS ETHICALLY BLOCKED until authentic licensed Indian optical imagery is acquired.
```

---

## 3. Data Usage Contracts & Restrictions

1. **Benchmark Models:**
   Models trained on Inria or SpaceNet 3 are benchmark champions. Their performance reflects standard remote-sensing vision tasks, **not** Indian cadastral surveying accuracy.
2. **OSM Reference Geometry:**
   Crowdsourced OpenStreetMap geometries are treated as advisory context only. They must never be described as legal property lines or statutory rights-of-way.
3. **Mumbai LULC Separation:**
   To prevent spatial and scientific leakage, Mumbai LULC data is strictly quarantined from Pune evaluation metrics.
