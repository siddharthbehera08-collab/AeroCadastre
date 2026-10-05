"""
Unit tests for Model A, Model B, and Model D Adapters.
Verifies:
1. Model A adapter returns BLOCKED_BY_IMAGERY_DATA when real imagery is missing.
2. Model A adapter operates cleanly on synthetic / reference-assisted inputs.
3. Model B adapter returns BLOCKED_BY_IMAGERY_DATA when real imagery is missing.
4. Model B adapter operates cleanly on synthetic / reference-assisted inputs.
5. Model D adapter extracts real Pune terrain statistics and enriches candidate parcels.
"""

from pathlib import Path
import pytest
from experiments.adapters.model_a_adapter import ModelABuildingAdapter
from experiments.adapters.model_b_adapter import ModelBRoadAdapter
from experiments.adapters.model_d_adapter import ModelDTerrainAdapter


def test_model_a_adapter_real_imagery_blocker():
    adapter = ModelABuildingAdapter()
    result = adapter.run_inference(
        raster_path=Path("nonexistent_pune_vhr.tif"),
        scene_id="PUNE_CORE_01",
        data_mode="REAL"
    )
    assert result["status"] == "BLOCKED_BY_IMAGERY_DATA"
    assert result["can_infer"] is False
    assert "MISSING" in result["reason"]
    assert result["provenance"]["status"] == "BLOCKED_BY_IMAGERY_DATA"


def test_model_a_adapter_synthetic_mode():
    adapter = ModelABuildingAdapter()
    sample_bldgs = [{"id": "B1", "properties": {"area": 120.0}}]
    result = adapter.run_inference(
        raster_path=None,
        scene_id="SYNTH_01",
        data_mode="SYNTHETIC",
        reference_buildings=sample_bldgs
    )
    assert result["status"] == "COMPLETED"
    assert result["feature_count"] == 1
    assert result["data_mode"] == "SYNTHETIC"
    assert result["provenance"]["crs"] == "EPSG:32643"


def test_model_b_adapter_real_imagery_blocker():
    adapter = ModelBRoadAdapter()
    result = adapter.run_inference(
        raster_path=None,
        scene_id="PUNE_CORE_01",
        data_mode="REAL"
    )
    assert result["status"] == "BLOCKED_BY_IMAGERY_DATA"
    assert result["can_infer"] is False
    assert "MISSING" in result["reason"]


def test_model_b_adapter_synthetic_mode():
    adapter = ModelBRoadAdapter()
    sample_roads = [{"id": "R1", "properties": {"highway": "residential"}}]
    result = adapter.run_inference(
        raster_path=None,
        scene_id="SYNTH_01",
        data_mode="SYNTHETIC",
        reference_roads=sample_roads
    )
    assert result["status"] == "COMPLETED"
    assert result["feature_count"] == 1
    assert result["data_mode"] == "SYNTHETIC"


def test_model_d_adapter_terrain_extraction_and_enrichment():
    adapter = ModelDTerrainAdapter()
    assert adapter.extractor is not None

    scene_res = adapter.extract_scene_terrain()
    assert scene_res["status"] == "COMPLETED"
    assert scene_res["data_mode"] == "REAL"
    assert "scene_statistics" in scene_res

    # Test parcel enrichment
    sample_parcel = {
        "id": "PARCEL_TEST_D",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[377600, 2047100], [377700, 2047100], [377700, 2047200], [377600, 2047200], [377600, 2047100]]]
        },
        "properties": {}
    }
    enriched = adapter.enrich_parcels_with_terrain([sample_parcel])
    assert len(enriched) == 1
    assert "terrain" in enriched[0]["properties"]
    assert "slope_mean" in enriched[0]["properties"]["terrain"] or "elevation_mean" in enriched[0]["properties"]["terrain"]
