"""Automated tests validating imagery audit, blocker documentation, and non-use of fake data."""
import os
import json
import pytest

PUNE_IMAGERY_DIR = r"D:\SIH26012_AeroCadastre\data\real\india\pune\imagery"
SOURCE_REGISTER_PATH = os.path.join(PUNE_IMAGERY_DIR, "IMAGERY_SOURCE_REGISTER.json")
BLOCKER_REPORT_PATH = os.path.join(PUNE_IMAGERY_DIR, "IMAGERY_BLOCKER_REPORT.md")
MANIFEST_PATH = os.path.join(PUNE_IMAGERY_DIR, "IMAGERY_MANIFEST.json")
ACQ_REPORT_PATH = os.path.join(PUNE_IMAGERY_DIR, "PUNE_IMAGERY_ACQUISITION_REPORT.md")
COV_REPORT_PATH = os.path.join(PUNE_IMAGERY_DIR, "IMAGERY_COVERAGE_REPORT.md")


def test_imagery_documentation_files_exist():
    """Verify that all required imagery audit documents and registries exist."""
    assert os.path.exists(SOURCE_REGISTER_PATH), "Missing IMAGERY_SOURCE_REGISTER.json"
    assert os.path.exists(BLOCKER_REPORT_PATH), "Missing IMAGERY_BLOCKER_REPORT.md"
    assert os.path.exists(MANIFEST_PATH), "Missing IMAGERY_MANIFEST.json"
    assert os.path.exists(ACQ_REPORT_PATH), "Missing PUNE_IMAGERY_ACQUISITION_REPORT.md"
    assert os.path.exists(COV_REPORT_PATH), "Missing IMAGERY_COVERAGE_REPORT.md"


def test_imagery_manifest_integrity_and_truthfulness():
    """Verify that the imagery manifest truthfully states MISSING status and does not claim fake files."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["imagery_status"] == "INDIAN_IMAGERY_STATUS = MISSING"
    assert len(data["acquired_rasters"]) == 0
    assert len(data["dependencies_blocked"]) > 0


def test_no_fake_optical_rasters_in_imagery_dir():
    """Verify that no fake, screenshot, or fabricated raster files exist in imagery/raw or imagery/processed."""
    raw_dir = os.path.join(PUNE_IMAGERY_DIR, "raw")
    proc_dir = os.path.join(PUNE_IMAGERY_DIR, "processed")
    assert os.path.exists(raw_dir)
    assert os.path.exists(proc_dir)
    raw_files = [f for f in os.listdir(raw_dir) if f.endswith(('.tif', '.png', '.jpg'))]
    proc_files = [f for f in os.listdir(proc_dir) if f.endswith(('.tif', '.png', '.jpg'))]
    assert len(raw_files) == 0, f"Found unexpected raw imagery files: {raw_files}"
    assert len(proc_files) == 0, f"Found unexpected processed imagery files: {proc_files}"


def test_source_register_covers_candidate_sources():
    """Verify that the source register exhaustively covers required government and open sources."""
    with open(SOURCE_REGISTER_PATH, "r", encoding="utf-8") as f:
        reg = json.load(f)
    sources = [s["source_name"] for s in reg["candidate_sources"]]
    assert any("Survey of India" in s for s in sources)
    assert any("Bhuvan" in s for s in sources)
    assert any("Sentinel-2" in s for s in sources)
    assert any("Landsat" in s for s in sources)
    assert reg["audit_conclusion"]["indian_imagery_status"] == "MISSING"
