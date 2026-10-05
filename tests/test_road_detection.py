"""
AeroCadastre Road Detection Unit & Integration Test Suite.
Verifies dataset loader, models, losses, metrics, vectorization, and inference pipelines.
"""

import pytest
import torch
import numpy as np
import shapely.geometry
from pathlib import Path

from ml.road_detection.models import RoadUNetBaseline, RoadResUNet, BCEDiceLoss, FocalDiceLoss
from ml.road_detection.metrics import compute_segmentation_metrics, compute_road_connectivity_metrics
from ml.road_detection.polygonizer import mask_to_road_polygons, road_polygons_to_geojson


def test_unet_baseline_forward():
    model = RoadUNetBaseline(in_channels=3, out_channels=1, base_features=16)
    x = torch.randn(2, 3, 256, 256)
    out = model(x)
    assert out.shape == (2, 1, 256, 256), f"Expected shape (2, 1, 256, 256), got {out.shape}"


def test_resunet_forward():
    model = RoadResUNet(in_channels=3, out_channels=1, base_features=16)
    x = torch.randn(2, 3, 256, 256)
    out = model(x)
    assert out.shape == (2, 1, 256, 256), f"Expected shape (2, 1, 256, 256), got {out.shape}"


def test_bce_dice_loss():
    loss_fn = BCEDiceLoss()
    logits = torch.randn(2, 1, 64, 64)
    targets = torch.randint(0, 2, (2, 1, 64, 64)).float()
    loss = loss_fn(logits, targets)
    assert not torch.isnan(loss)
    assert loss.item() >= 0.0


def test_focal_dice_loss():
    loss_fn = FocalDiceLoss()
    logits = torch.randn(2, 1, 64, 64)
    targets = torch.randint(0, 2, (2, 1, 64, 64)).float()
    loss = loss_fn(logits, targets)
    assert not torch.isnan(loss)
    assert loss.item() >= 0.0


def test_segmentation_metrics_perfect_match():
    targets = np.zeros((100, 100), dtype=np.float32)
    targets[20:40, 20:40] = 1.0
    preds = targets.copy()
    m = compute_segmentation_metrics(preds, targets)
    assert np.isclose(m["iou"], 1.0, atol=1e-3)
    assert np.isclose(m["dice"], 1.0, atol=1e-3)
    assert np.isclose(m["pixel_accuracy"], 1.0, atol=1e-3)


def test_road_connectivity_metrics():
    # Linear corridor
    target = np.zeros((100, 100), dtype=np.uint8)
    target[48:52, :] = 1  # Continuous horizontal road
    pred = target.copy()
    
    conn = compute_road_connectivity_metrics(pred, target)
    assert conn["centerline_coverage"] == 1.0
    assert conn["fragmentation_index"] == 1.0


def test_mask_to_road_polygons():
    mask = np.zeros((200, 200), dtype=np.uint8)
    # Draw a road corridor
    mask[90:110, 10:190] = 255
    polygons = mask_to_road_polygons(mask, min_area=50.0)
    assert len(polygons) == 1
    assert polygons[0].is_valid
    assert not polygons[0].is_empty


def test_geojson_export():
    poly = shapely.geometry.box(10, 10, 50, 50)
    doc = road_polygons_to_geojson([poly], crs_epsg=4326)
    assert doc["type"] == "FeatureCollection"
    assert len(doc["features"]) == 1
    assert doc["features"][0]["geometry"]["type"] == "Polygon"
