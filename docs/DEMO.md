# SIH26012 — AeroCadastre: End-to-End Demo Walkthrough (`DEMO.md`)

## Complete 24-Step Demonstration Flow

1. **Dashboard (`01. Dashboard`):** Observe real database counts for `scene_urban_T1` (Candidate Parcels, Buildings, Roads, Topology Issues, GIS Conflicts, Anomalies, Pending Verification, ML Experiments) clearly labeled `SYNTHETIC DEMO DATA`.
2. **Mapping Workspace (`02. Mapping Workspace`):**
   - Toggle layers (`Drone Ortho RGB`, `AI Parcels`, `Ref GIS Layer`, `Buildings`, `Road Corridors`, `Boundary Types`, `Topology Issues`, `Conflicts/Anom.`, `Field Route`).
   - Click `scene_urban_T1_P_002` (which has an active `OVERLAP` with `P_001`).
   - Click **Snap to Ref GIS** or drag vertices `v1..v4` on the map canvas, change Land-Use, and click **✓ Verify Parcel** (`Save Geometry & Attributes to PostGIS`).
   - Observe that the `OVERLAP` topology issue immediately disappears and `P_002` turns cyan (`HUMAN_VERIFIED`).
   - Test **Split Parcel** and **Merge** or **+ Digitize New Candidate Parcel**.
3. **AI Analysis (`03. AI Analysis & Models`):** Inspect all 8 trained models (`EXP_001`..`EXP_008`), comparing `SimpleCNNSeg` (`0.8915` IoU) vs `MicroResUNet_RGBD_v2` (`0.9995` IoU) and `LandUse_MicroUNet` (`0.4924` IoU) vs `LandUse_MicroResUNet_Weighted_v2` (`0.8396` IoU).
4. **AI Council (`04. AI Council`):** Inspect the 6 domain agents (`VISION`, `GEOMETRY`, `GIS`, `ML`, `ANOMALY`, `FIELD_VERIFICATION`) and the `COUNCIL FUSION` verdict.
5. **Change Detection & Parcel Time Machine (`06` & `07`):** Compare `2024 (T0)`, `2025 (T1)`, `2026 (T2)` and human edit versions (`HUMAN_EDIT`).
6. **Smart Field Route & Cadastral AI Copilot (`08` & `09`):** View spatially clustered verification routes and ask the Copilot `"Why was parcel P-003 flagged?"` or `"Which parcels overlap?"`.
7. **Validated GIS Exports (`12. GIS Exports`):** Export to `GeoJSON`, `Shapefile (.zip)`, `CSV`, and `GeoPackage (.gpkg)` and verify the post-export read-back integrity check passes.
