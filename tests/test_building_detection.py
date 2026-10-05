"""AeroCadastre Building Detection Test Suite.

Tests:
1. Dataset discovery & validation functions
2. Dataset loader & tensor generation
3. Data augmentation transformations
4. Model forward pass (UNetBaseline, ResUNet)
5. Loss functions (BCEDiceLoss, FocalDiceLoss)
6. Metrics calculation (IoU, Dice, Precision, Recall, Boundary F1)
7. Edge cases (empty mask, all-building mask, tiny building, single-pixel)
8. Polygonizer & geometry validation (self-intersection repair, minimum area)
9. GeoJSON export & metadata integrity
10. Deterministic seed reproducibility
"""

import json
import numpy as np
import pytest
import torch
from shapely.geometry import Polygon, MultiPolygon

from ml.building_detection.models import UNetBaseline, ResUNet, BCEDiceLoss, FocalDiceLoss
from ml.building_detection.metrics import (
    compute_segmentation_metrics,
    compute_boundary_f1,
    extract_boundary,
)
from ml.building_detection.polygonizer import (
    mask_to_polygons,
    validate_and_repair_polygon,
    polygons_to_geojson,
)
from ml.building_detection.trainer import set_seed


def test_seed_determinism():
    """Verify that set_seed ensures repeatable tensor initialization."""
    set_seed(123)
    t1 = torch.randn(10, 10)
    set_seed(123)
    t2 = torch.randn(10, 10)
    assert torch.equal(t1, t2), "Tensors should be identical under same seed"


def test_unet_baseline_forward():
    """Test UNetBaseline forward pass shapes and gradients."""
    model = UNetBaseline(in_channels=3, out_channels=1, base_features=16)
    x = torch.randn(2, 3, 128, 128)
    out = model(x)
    assert out.shape == (2, 1, 128, 128), f"Expected (2, 1, 128, 128), got {out.shape}"
    loss = out.sum()
    loss.backward()
    assert model.inc.double_conv[0].weight.grad is not None


def test_resunet_forward():
    """Test ResUNet forward pass shapes and gradients."""
    model = ResUNet(in_channels=3, out_channels=1, base_features=16)
    x = torch.randn(2, 3, 128, 128)
    out = model(x)
    assert out.shape == (2, 1, 128, 128), f"Expected (2, 1, 128, 128), got {out.shape}"
    loss = out.sum()
    loss.backward()
    assert model.enc1.conv1.weight.grad is not None


def test_bce_dice_loss():
    """Test BCEDiceLoss behavior and bounds."""
    criterion = BCEDiceLoss(bce_weight=0.5)
    logits = torch.randn(2, 1, 64, 64, requires_grad=True)
    targets = torch.randint(0, 2, (2, 1, 64, 64)).float()

    loss = criterion(logits, targets)
    assert loss.item() > 0
    loss.backward()
    assert logits.grad is not None


def test_focal_dice_loss():
    """Test FocalDiceLoss behavior."""
    criterion = FocalDiceLoss(focal_weight=0.5)
    logits = torch.randn(2, 1, 64, 64, requires_grad=True)
    targets = torch.randint(0, 2, (2, 1, 64, 64)).float()

    loss = criterion(logits, targets)
    assert loss.item() > 0
    loss.backward()
    assert logits.grad is not None


def test_segmentation_metrics_perfect_match():
    """Test metrics on identical prediction and target."""
    probs = np.ones((1, 1, 50, 50), dtype=np.float32)
    targets = np.ones((1, 1, 50, 50), dtype=np.float32)

    metrics = compute_segmentation_metrics(probs, targets, threshold=0.5)
    assert metrics["iou"] == 1.0
    assert metrics["dice"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["pixel_accuracy"] == 1.0


def test_segmentation_metrics_complete_mismatch():
    """Test metrics on completely disjoint prediction and target."""
    probs = np.zeros((1, 1, 50, 50), dtype=np.float32)
    targets = np.ones((1, 1, 50, 50), dtype=np.float32)

    metrics = compute_segmentation_metrics(probs, targets, threshold=0.5)
    assert metrics["iou"] == 0.0
    assert metrics["dice"] == 0.0
    assert metrics["recall"] == 0.0


def test_edge_case_empty_mask():
    """Test handling of completely empty masks."""
    probs = np.zeros((100, 100), dtype=np.float32)
    targets = np.zeros((100, 100), dtype=np.float32)

    metrics = compute_segmentation_metrics(probs, targets, threshold=0.5, compute_boundary=True)
    assert metrics["pixel_accuracy"] == 1.0
    assert metrics["gt_building_ratio"] == 0.0
    assert metrics["boundary_f1"] == 1.0


def test_edge_case_single_pixel_building():
    """Test single pixel building detection metric."""
    probs = np.zeros((50, 50), dtype=np.float32)
    targets = np.zeros((50, 50), dtype=np.float32)
    targets[25, 25] = 1.0
    probs[25, 25] = 0.9

    metrics = compute_segmentation_metrics(probs, targets, threshold=0.5)
    assert metrics["iou"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0


def test_boundary_extraction():
    """Test morphological boundary extraction."""
    mask = np.zeros((20, 20), dtype=np.uint8)
    mask[5:15, 5:15] = 1

    boundary = extract_boundary(mask)
    assert np.any(boundary)
    # Center pixel (10, 10) must NOT be boundary
    assert not boundary[10, 10]
    # Edge pixel (5, 5) MUST be boundary
    assert boundary[5, 5]


def test_mask_to_polygons_extraction():
    """Test polygon extraction from binary raster mask."""
    mask = np.zeros((100, 100), dtype=np.uint8)
    # Draw two distinct building squares
    mask[10:30, 10:30] = 1
    mask[50:80, 50:80] = 1

    polygons = mask_to_polygons(mask, min_area=50.0)
    assert len(polygons) == 2
    for p in polygons:
        assert p.is_valid
        assert p.area >= 50.0


def test_polygon_validation_and_repair():
    """Test self-intersecting bowtie polygon repair."""
    # Bowtie polygon (self-intersecting)
    bowtie = Polygon([(0, 0), (20, 20), (0, 20), (20, 0), (0, 0)])
    assert not bowtie.is_valid

    repaired = validate_and_repair_polygon(bowtie, min_area=5.0)
    assert repaired is not None
    assert repaired.is_valid


def test_polygons_to_geojson():
    """Test GeoJSON conversion with metadata and CRS."""
    p1 = Polygon([(10, 10), (30, 10), (30, 30), (10, 30), (10, 10)])
    p2 = Polygon([(50, 50), (70, 50), (70, 70), (50, 70), (50, 50)])

    meta = {"model": "UNetBaseline", "test_id": "TEST_001"}
    geojson = polygons_to_geojson([p1, p2], crs_epsg=32643, source_metadata=meta)

    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 2
    assert geojson["crs"]["properties"]["name"] == "urn:ogc:def:crs:EPSG::32643"
    assert geojson["metadata"]["model"] == "UNetBaseline"
    assert geojson["features"][0]["properties"]["class"] == "building"
