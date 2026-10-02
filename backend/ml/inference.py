import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import numpy as np
from PIL import Image, UnidentifiedImageError
import torch

from backend.config import MODELS_DIR, LAND_USE_CLASSES
from backend.ml.architectures import MicroUNet, MicroResUNet


class GeoAIInferenceEngine:
    """Loads trained checkpoints from D:/SIH26012_AeroCadastre/models and runs real GeoAI inference."""

    def __init__(self):
        self.models_loaded = False
        self.bldg_primary = None
        self.bldg_secondary = None
        self.road_model = None
        self.bnd_model = None
        self.lu_model = None

    def ensure_loaded(self):
        if self.models_loaded:
            return
        p_bldg3 = MODELS_DIR / "EXP_003_Building_MicroResUNet_RGBD_v2.pt"
        p_bldg2 = MODELS_DIR / "EXP_002_Building_MicroUNet_v1.pt"
        p_road = MODELS_DIR / "EXP_004_Road_MicroUNet_v1.pt"
        p_bnd = MODELS_DIR / "EXP_005_Boundary_MicroResUNet_v1.pt"
        p_lu8 = MODELS_DIR / "EXP_008_LandUse_MicroResUNet_Weighted_v2.pt"
        p_lu7 = MODELS_DIR / "EXP_007_LandUse_MicroUNet.pt"

        if p_bldg3.exists():
            ckpt = torch.load(p_bldg3, map_location="cpu", weights_only=False)
            m = MicroResUNet(in_channels=4, out_channels=1, base_ch=14)
            m.load_state_dict(ckpt["state_dict"])
            m.eval()
            self.bldg_primary = m

        if p_bldg2.exists():
            ckpt = torch.load(p_bldg2, map_location="cpu", weights_only=False)
            m = MicroUNet(in_channels=3, out_channels=1, base_ch=12)
            m.load_state_dict(ckpt["state_dict"])
            m.eval()
            self.bldg_secondary = m

        if p_road.exists():
            ckpt = torch.load(p_road, map_location="cpu", weights_only=False)
            m = MicroUNet(in_channels=3, out_channels=1, base_ch=12)
            m.load_state_dict(ckpt["state_dict"])
            m.eval()
            self.road_model = m

        if p_bnd.exists():
            ckpt = torch.load(p_bnd, map_location="cpu", weights_only=False)
            m = MicroResUNet(in_channels=4, out_channels=1, base_ch=12)
            m.load_state_dict(ckpt["state_dict"])
            m.eval()
            self.bnd_model = m

        if p_lu8.exists():
            ckpt = torch.load(p_lu8, map_location="cpu", weights_only=False)
            m = MicroResUNet(in_channels=4, out_channels=len(LAND_USE_CLASSES), base_ch=16)
            m.load_state_dict(ckpt["state_dict"])
            m.eval()
            self.lu_model = m
        elif p_lu7.exists():
            ckpt = torch.load(p_lu7, map_location="cpu", weights_only=False)
            m = MicroUNet(in_channels=4, out_channels=len(LAND_USE_CLASSES), base_ch=16)
            m.load_state_dict(ckpt["state_dict"])
            m.eval()
            self.lu_model = m

        self.models_loaded = any([self.bldg_primary, self.road_model, self.bnd_model, self.lu_model])

    def validate_and_prepare_arrays(
        self, rgb: np.ndarray, dsm: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Validate imagery array dimensions, channels, dtype, and finite values before inference."""
        if not isinstance(rgb, np.ndarray):
            raise ValueError("Input rgb must be a numpy.ndarray.")
        if not np.issubdtype(rgb.dtype, np.number) or rgb.dtype == np.bool_:
            raise ValueError(f"Unexpected non-numeric dtype '{rgb.dtype}' for imagery.")
        if rgb.size == 0:
            raise ValueError("Empty image array provided (size == 0).")
        if rgb.ndim != 3:
            raise ValueError(
                f"Wrong tensor dimensions: expected 3D array (H, W, C), got shape {rgb.shape}."
            )
        h, w, c = rgb.shape
        if c not in (3, 4):
            raise ValueError(
                f"Wrong channel count: expected 3 (RGB) or 4 (RGBA/RGBD) channels, got {c}."
            )
        if h < 16 or w < 16 or (h % 4 != 0) or (w % 4 != 0):
            raise ValueError(
                f"Wrong spatial dimensions ({h}x{w}): height and width must be >= 16 and divisible by 4."
            )
        if not np.all(np.isfinite(rgb)):
            raise ValueError("Image contains NaN or Inf values.")

        rgb_f = rgb[:, :, :3].astype(np.float32)
        if rgb_f.max() > 1.5:
            rgb_f = rgb_f / 255.0
        if float(np.max(rgb_f)) <= 0.0 and float(np.min(rgb_f)) >= 0.0:
            raise ValueError("Empty all-zero image array provided.")

        if dsm is not None:
            if not isinstance(dsm, np.ndarray) or dsm.shape != (h, w):
                raise ValueError(
                    f"DSM shape {getattr(dsm, 'shape', None)} does not match RGB spatial dimensions ({h}, {w})."
                )
            if not np.issubdtype(dsm.dtype, np.number) or not np.all(np.isfinite(dsm)):
                raise ValueError("Invalid DSM dtype or non-finite values.")
            dsm_f = dsm.astype(np.float32)
        else:
            dsm_f = np.full((h, w), 215.0, dtype=np.float32)

        ndsm = np.clip((dsm_f - np.percentile(dsm_f, 15)) / 12.0, 0.0, 1.5).astype(np.float32)
        return rgb_f, dsm_f, ndsm

    def run_array_inference(
        self,
        rgb: np.ndarray,
        dsm: Optional[np.ndarray] = None,
        scene_id: str = "inline_array",
        origin_lonlat: Tuple[float, float] = (77.592, 12.972),
    ) -> Dict[str, Any]:
        """Run multi-model PyTorch inference directly on validated numpy arrays."""
        self.ensure_loaded()
        t0 = time.perf_counter()
        rgb_f, dsm_f, ndsm = self.validate_and_prepare_arrays(rgb, dsm)
        h, w, _ = rgb_f.shape

        rgb_t = torch.from_numpy(np.transpose(rgb_f, (2, 0, 1))[None, :, :, :])
        rgbd_np = np.concatenate([np.transpose(rgb_f, (2, 0, 1)), ndsm[None, :, :]], axis=0)[
            None, :, :, :
        ]
        rgbd_t = torch.from_numpy(rgbd_np)

        with torch.no_grad():
            if self.bldg_primary is not None:
                bldg_prob = torch.sigmoid(self.bldg_primary(rgbd_t))[0, 0].numpy()
            else:
                bldg_prob = (ndsm > 0.25).astype(np.float32) * 0.85

            if self.bldg_secondary is not None:
                bldg_sec_prob = torch.sigmoid(self.bldg_secondary(rgb_t))[0, 0].numpy()
            else:
                bldg_sec_prob = bldg_prob * 0.95

            if self.road_model is not None:
                road_prob = torch.sigmoid(self.road_model(rgb_t))[0, 0].numpy()
            else:
                road_prob = np.zeros((h, w), dtype=np.float32)

            if self.bnd_model is not None:
                bnd_prob = torch.sigmoid(self.bnd_model(rgbd_t))[0, 0].numpy()
            else:
                bnd_prob = np.zeros((h, w), dtype=np.float32)

            if self.lu_model is not None:
                lu_logits = self.lu_model(rgbd_t)[0]
                lu_probs = torch.softmax(lu_logits, dim=0).numpy()
                lu_pred = np.argmax(lu_probs, axis=0)
                lu_conf = np.max(lu_probs, axis=0)
            else:
                lu_pred = np.full((h, w), 1, dtype=np.int64)
                lu_conf = np.full((h, w), 0.78, dtype=np.float32)

        model_disagreement = np.abs(bldg_prob - bldg_sec_prob)
        inference_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        return {
            "scene_id": scene_id,
            "size": h,
            "origin_lonlat": origin_lonlat,
            "dsm": dsm_f,
            "ndsm": ndsm,
            "bldg_prob": bldg_prob,
            "bldg_sec_prob": bldg_sec_prob,
            "model_disagreement": model_disagreement,
            "road_prob": road_prob,
            "bnd_prob": bnd_prob,
            "lu_pred": lu_pred,
            "lu_conf": lu_conf,
            "inference_time_ms": inference_ms,
            "models_used": {
                "building_primary": "Building_MicroResUNet_RGBD_v2 (EXP_003)"
                if self.bldg_primary
                else "Fallback_nDSM",
                "building_secondary": "Building_MicroUNet_v1 (EXP_002)"
                if self.bldg_secondary
                else "Fallback_RGB",
                "road": "Road_MicroUNet_v1 (EXP_004)" if self.road_model else "Fallback_Road",
                "boundary": "Boundary_MicroResUNet_v1 (EXP_005)"
                if self.bnd_model
                else "Fallback_Boundary",
                "landuse": "LandUse_MicroUNet_RGBD (EXP_007)"
                if self.lu_model
                else "Fallback_LandUse",
            },
        }

    def run_scene_inference(self, scene_dir: Path) -> Dict[str, Any]:
        """Run full multi-model GeoAI inference on a scene directory."""
        if not scene_dir.exists() or not scene_dir.is_dir():
            raise FileNotFoundError(f"Scene directory '{scene_dir}' does not exist.")
        meta_path = scene_dir / "metadata.json"
        rgb_path = scene_dir / "rgb.png"
        if not meta_path.exists():
            raise FileNotFoundError(f"Missing metadata.json in '{scene_dir}'.")
        if not rgb_path.exists():
            raise FileNotFoundError(f"Missing rgb.png in '{scene_dir}'.")

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"Corrupt metadata.json in '{scene_dir}': {exc}") from exc

        try:
            with Image.open(rgb_path) as im:
                im.verify()
            with Image.open(rgb_path) as im2:
                rgb_raw = np.array(im2)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ValueError(f"Corrupt or unreadable image '{rgb_path}': {exc}") from exc

        if rgb_raw.ndim == 2:
            raise ValueError("Wrong channel count: grayscale 1-channel image is not supported; 3-channel RGB required.")

        size = meta["image_size"][0]
        origin_lon, origin_lat = meta["origin_lonlat"]

        dsm = None
        if (scene_dir / "dsm.npy").exists():
            try:
                dsm = np.load(scene_dir / "dsm.npy").astype(np.float32)
            except Exception as exc:
                raise ValueError(f"Corrupt DSM array in '{scene_dir}/dsm.npy': {exc}") from exc

        return self.run_array_inference(
            rgb=rgb_raw,
            dsm=dsm,
            scene_id=meta["scene_id"],
            origin_lonlat=(origin_lon, origin_lat),
        )


inference_engine = GeoAIInferenceEngine()
