"""
Unit tests for Model I Change Detection Engine.
Verifies:
1. Real imagery returns BLOCKED_BY_IMAGERY_DATA without fabricating temporal difference maps.
2. Synthetic mode returns EXPERIMENTAL_ONLY change candidate vectors.
3. Provenance and governance disclaimers are preserved.
"""

from pathlib import Path
import pytest
from experiments.model_i_change.change_detector import ChangeDetectionEngine


def test_model_i_real_imagery_blocker():
    engine = ChangeDetectionEngine()
    result = engine.detect_change_between_rasters(
        raster_t1_path=None,
        raster_t2_path=None,
        data_mode="REAL"
    )
    assert result["status"] == "BLOCKED_BY_IMAGERY_DATA"
    assert result["can_infer"] is False
    assert "MISSING" in result["reason"]
    assert result["provenance"]["status"] == "BLOCKED_BY_IMAGERY_DATA"


def test_model_i_synthetic_experimental_execution():
    engine = ChangeDetectionEngine()
    result = engine.detect_change_between_rasters(
        raster_t1_path=None,
        raster_t2_path=None,
        data_mode="SYNTHETIC"
    )
    assert result["status"] == "COMPLETED"
    assert result["experimental_only"] is True
    assert result["supplementary_only"] is True
    assert result["change_count"] == 1
    assert "NEW_STRUCTURE_CONSTRUCTED" in result["changes"][0]["type"]
    assert result["provenance"]["crs"] == "EPSG:32643"
