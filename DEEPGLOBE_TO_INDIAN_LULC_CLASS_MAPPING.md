# DeepGlobe to Indian Cadastral / LULC Class Mapping
**Project:** SIH26012 — AI-Based Automated Urban Parcel Mapping and Cadastral Feature Extraction System using Drone Imagery  
**Document Code:** `DEEPGLOBE_TO_INDIAN_LULC_CLASS_MAPPING.md`  
**Date:** October 2026  
**Status:** Canonical Reference Specification  

---

## 1. Context & Objective

The **DeepGlobe Land Cover Classification Dataset** provides satellite imagery (0.5 m GSD) annotated with a 7-class taxonomy focused on macro-landscape categories. In contrast, the Indian cadastral and land-administration ecosystem—governed by the **Department of Land Resources (DoLR)**, the **National Remote Sensing Centre (NRSC / ISRO Bhuvan)**, and the **Survey of India (SOI)**—operates on standard multi-tier hierarchical classification systems (such as the **NRSC National LULC 1:50,000 / 1:10,000 SIS-DP classification** and municipal City Survey CTS land-use schedules).

To train, transfer-learn, or fine-tune multi-task GeoAI models for AeroCadastre without introducing semantic leakage or legal confusion:
1. **Building footprints are NOT cadastral parcel boundaries.**
2. **Roads are NOT automatically legal rights-of-way (RoW).**
3. **DeepGlobe macro-classes CANNOT be directly substituted for Indian statutory land parcel tenures.**

This document defines the rigorous semantic translation and crosswalk matrix between the DeepGlobe 7-class schema, the NRSC/Bhuvan Level-1/2 taxonomy, and the Urban Cadastral (NAKSHA/CTS) property tenures.

---

## 2. Taxonomy Schema Crosswalk

| DeepGlobe Class (ID & RGB) | DeepGlobe Description | NRSC / ISRO Bhuvan Equivalent (Level 1 / 2) | Indian Cadastral / NAKSHA Tenure Category | AeroCadastre Functional AI Mapping |
|---|---|---|---|---|
| **Urban Land**<br>`(0, 255, 255)` — Cyan | Man-made structures, built-up areas, concrete/asphalt | **Built-up (Code 01)**<br>• Urban Built-up (0101)<br>• Rural Built-up / Gaothan (0102)<br>• Industrial / Commercial (0103) | **Built-up Urban Parcel (CTS Property Card / UrPro)**<br>• Residential Land Parcel<br>• Commercial / Mixed Plot<br>• Municipal Public Amenity | Maps to **Model A (Building Detection)** & **Model C (Urban Built-up Class)**. Sub-segmented into individual parcels using polygonization and party-wall boundary inference. |
| **Agriculture Land**<br>`(255, 255, 0)` — Yellow | Cropland, planted fields, orchards, irrigated lands | **Agricultural Land (Code 02)**<br>• Crop Land (Kharif / Rabi / Zaid)<br>• Fallow Land (Current / Permanent)<br>• Plantations | **Agricultural Survey / Gat Number (7/12 Extract)**<br>• Irrigated (*Bagayat*)<br>• Rainfed (*Jirayat*)<br>• Fallow / Non-cultivated | Maps to **Model C (Agricultural LULC)** & **Model E (Cadastral Boundary - Field Bund Inference)**. Bund lines provide natural parcel divider candidates. |
| **Rangeland**<br>`(255, 0, 255)` — Magenta | Scrubland, grassland, unmanaged open pastures | **Wastelands / Grazing Land (Code 04 / 05)**<br>• Scrubland (Dense / Open)<br>• Pasture / Grazing Land (*Gairan*) | **Government / Village Common Land (*Gairan*)**<br>• Revenue Waste Land<br>• Gram Panchayat Grazing Parcel | Maps to **Model C (Scrub/Rangeland)** & **Model G (Encroachment Anomaly Detection)** on village common lands. |
| **Forest Land**<br>`(0, 255, 0)` — Green | Natural/semi-natural tree cover, dense canopy | **Forest (Code 03)**<br>• Evergreen / Deciduous<br>• Scrub Forest<br>• Forest Plantation | **Reserved / Protected Forest Cadastre**<br>• Reserved Forest (RF compartment boundaries)<br>• Protected Forest (PF)<br>• Mangrove conservation zones | Maps to **Model C (Forest/Tree Canopy)** and environmental buffer restriction zones in GIS conflict detection. |
| **Water**<br>`(0, 0, 255)` — Blue | Rivers, streams, lakes, ponds, canals, reservoirs | **Water Bodies (Code 06)**<br>• River / Stream / *Nala*<br>• Lake / Tank / Pond<br>• Canal / Water Course | **Government Water Resource (*Jalashay / Nala Boundary*)**<br>• Natural Watercourse (*Nala* / *Odha*)<br>• Water Body Protection Buffer (*Blue / Red Flood Lines*) | Maps to **Model C (Water)** & **Model L (GIS Conflict / Natural Drain Encroachment)**. Cadastral parcels intersecting active waterways trigger high priority field verification. |
| **Barren Land**<br>`(255, 255, 255)` — White | Rocks, exposed soil, sand, bare ground, excavation | **Barren / Unculturable Land (Code 05)**<br>• Barren Rocky<br>• Gullied / Ravinous Land<br>• Sandy / River Sand | **Unculturable Government Land (*Padit Jameen*)**<br>• Quarry / Mining Parcel<br>• Rocky Waste | Maps to **Model C (Barren Soil/Rock)**. Distinguishes unbuilt vacant cadastral plots from actively excavated infrastructure zones. |
| **Unknown / Background**<br>`(0, 0, 0)` — Black | Clouds, shadows, unclassified artifacts | **Unclassified / Cloud Shadow** | **Unsurveyed Area / Cloud Obstruction** | Filtered during pre-processing; flagged for cloud-masking or manual aerial re-survey. |

---

## 3. Road Network Semantic Disaggregation

In the DeepGlobe Road Extraction dataset, roads are labeled as a single binary raster class. In Indian cadastral administration, transport corridors are divided into distinct legal tiers:

| DeepGlobe Road Label | Indian Cadastral & Infrastructure Classification | Administrative Jurisdiction | Legal Cadastral Property |
|---|---|---|---|
| **Binary Road Mask (Value 255)** | **National Highway / State Highway (NH / SH)** | MoRTH / State PWD | Statutory Right-of-Way (RoW) corridor; building setbacks mandatory (15m–30m). |
| **Binary Road Mask (Value 255)** | **Major District Road / Other District Road (MDR / ODR)** | Zilla Parishad / PWD | Public roadway easement separating agricultural Gat numbers. |
| **Binary Road Mask (Value 255)** | **Municipal DP Road / Sector Road** | Municipal Corporation (e.g. PMC / PCMC) | Dedicated municipal road reserve mapped in City Development Plan (DP). |
| **Binary Road Mask (Value 255)** | **Village Access Pathway (*Shetrasta* / Cart Track)** | Revenue Department / Gram Panchayat | Customary easement across private land; not always surveyed as a separate parcel. |
| **Binary Road Mask (Value 255)** | **Peth Gully / Private Access Lane** | Private Society / Shared Co-owners | Shared internal accessway; party to adjacent building deeds. |

> **Critical Rule:** When performing automated parcel boundary inference (**Model E**), detected road centerlines must be buffered according to municipal road hierarchy standards rather than simply converted directly into cadastral parcel polygons.

---

## 4. Class Harmonization Implementation Guidelines

When converting DeepGlobe predictions for downstream inference inside AeroCadastre:

```python
# Semantic remapping dictionary from DeepGlobe RGB tuples to AeroCadastre LULC IDs
DEEPGLOBE_TO_AEROCADASTRE_LULC = {
    (0, 255, 255): {"class_id": 1, "name": "built_up", "cadastral_type": "urban_parcel"},
    (255, 255, 0): {"class_id": 2, "name": "agriculture", "cadastral_type": "agricultural_gat"},
    (255, 0, 255): {"class_id": 3, "name": "rangeland", "cadastral_type": "village_commons_gairan"},
    (0, 255, 0):   {"class_id": 4, "name": "forest", "cadastral_type": "reserved_forest"},
    (0, 0, 255):   {"class_id": 5, "name": "water_body", "cadastral_type": "watercourse_buffer"},
    (255, 255, 255): {"class_id": 6, "name": "barren", "cadastral_type": "vacant_unbuilt"},
    (0, 0, 0):     {"class_id": 0, "name": "unclassified", "cadastral_type": "nodata"}
}
```

This mapping prevents accidental misuse of macroscopic land-cover labels in municipal cadastral enforcement workflows.
