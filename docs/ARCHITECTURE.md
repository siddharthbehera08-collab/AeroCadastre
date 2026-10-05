# AeroCadastre SIH26012 — System Architecture Specification
**Document Date:** 2026-10-04  
**Framework Version:** AeroCadastre Core v2.0  

---

## 1. High-Level System Architecture Diagram

```
[ Multi-Modal Input Data Sources ]
  ├── Optical VHR Orthoimagery (ResUNet Model A / B)
  ├── SRTM / Cartosat Elevation Rasters (Model D Terrain Analysis)
  └── Reference Vector Overlays (OpenStreetMap Pune Reference Layers)
                    │
                    ▼
[ Layer 1: Feature Extraction & Boundary Evidence Engine ]
  ├── Model A: Building Footprints & Rooftop Boundaries
  ├── Model B: Road Surface Extraction & Centerline Corridors
  ├── Model D: Slope, Aspect, Relief, and Elevation Derivatives
  └── Boundary Evidence Engine: Distance, Angle, and Likelihood Features
                    │
                    ▼
[ Layer 2: Multi-Source Spatial Evidence Fusion (Model E) ]
  ├── 6-Domain Evidence Renormalization (Building, Road, Boundary, Terrain, Reference, LULC)
  ├── Dynamic Weight Normalization (Missing evidence never penalized as negative)
  └── Inter-Model Disagreement & Uncertainty Scoring
                    │
                    ▼
[ Layer 3: Parcel Inference & Planarization Engine (Model F) ]
  ├── Planar Voronoi / Delaunay & Line Network Planarization
  ├── Exterior & Interior Polygon Ring Extraction
  ├── Sliver & Tiny Polygon Filtering (min_area_m2 threshold)
  └── Candidate Parcel Generation: CANDIDATE_PARCEL / INFERRED_PARCEL_BOUNDARY
                    │
                    ▼
[ Layer 4: Computational Geometry & Anomaly Engines (Models G & H) ]
  ├── Model G (Topology): Self-Intersections, Overlaps, Gaps, Polsby-Popper Compactness
  └── Model H (Anomaly): Cross-layer Building/Road Conflicts & Sliver Discrepancies
                    │
                    ▼
[ Layer 5: Deterministic Bayesian Confidence Engine ]
  ├── Multi-Criteria Evidence Breakdown (Model confidence, Compactness, Completeness, GIS IoU)
  └── Categorical Confidence Bands (HIGH / MEDIUM / LOW / REJECT)
                    │
                    ▼
[ Layer 6: AI Council Multi-Agent Adjudication ]
  ├── 6 Specialized Autonomous Agents:
  │     1. Vision Agent (Model A/B confidence & edge clarity)
  │     2. Geometry Agent (Compactness & perimeter regularity)
  │     3. GIS Agent (Reference alignment & road access)
  │     4. ML Agent (Model agreement & uncertainty variance)
  │     5. Anomaly Agent (Cross-layer structural conflicts)
  │     6. Field Verification Agent (Inspection prioritization & reasons)
  └── Precedence Consensus Decision: ACCEPT_FOR_REVIEW / REQUIRES_VERIFICATION
                    │
                    ▼
[ Layer 7: Human-in-the-Loop (HITL) WebGIS & Surveyor Support ]
  ├── Smart Field Route Planner: Metric TSP Nearest-Neighbor Inspection Tour
  ├── Parcel Time Machine: Version Diffing (Hausdorff Boundary Displacement & IoU Variances)
  ├── Cadastral AI Copilot: Grounded Natural-Language Explanations (Strict Non-Ownership Policy)
  └── Active Learning Feedback Export: Prospective Model Tuning Datasets & Manifests
                    │
                    ▼
[ Layer 8: Pre-Cadastre GIS Export & Provenance Assurance ]
  ├── Formats: GeoJSON, GeoPackage, Shapefile (.zip)
  ├── Statutory Status: NOT_ASSIGNED_PRE_CADASTRE
  └── Cryptographic Audit Trail: SHA256 checksums, CRS metadata (EPSG:32643)
```

---

## 2. Core Architectural Guarantees

1. **Deterministic Execution:**
   All computational geometry, confidence scoring, topology repair, and field route planning operations use deterministic algorithms with zero random seeds, ensuring 100% reproducible results.
2. **Graceful Multi-Modal Degradation:**
   When optical or auxiliary reference layers are unavailable, the fusion engine dynamically redistributes attention to remaining physical priors (e.g., terrain slopes) without inventing false evidence.
3. **Strict Decoupling of Authority:**
   The AI system acts purely as an advisory decision-support assistant. No property ownership, deed attribution, or official statutory ULPIN numbers are ever generated.
