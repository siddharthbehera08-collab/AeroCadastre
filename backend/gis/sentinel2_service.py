"""
AeroCadastre Sentinel-2 L2A Acquisition & Processing Engine.
Acquires real Sentinel-2 L2A multispectral data from Microsoft Planetary Computer
for the Pune Study Area using bounded, windowed AOI requests with explicit timeouts.

Generates:
- B02 (Blue, 10m)
- B03 (Green, 10m)
- B04 (Red, 10m)
- B08 (NIR, 10m)
- RGB True-Color Composite (3-band GeoTIFF)
- NDVI (Normalized Difference Vegetation Index, Float32 GeoTIFF)
- SCL (Scene Classification Layer, 20m)
- Cryptographic provenance metadata with SHA256 hashes

Governed by:
- Scientific Limitation: Sentinel-2 is contextual / LULC evidence, not cadastral parcel truth.
- Zero Key Leakage & Bounded Network I/O.
"""

import hashlib
import io
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import rasterio
from rasterio.transform import Affine
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sentinel2_service")

# Default Targets & Constants
DEFAULT_ITEM_ID = "S2A_MSIL2A_20261002T053241_R105_T43QCA_20261002T101803"
STAC_API_URL = f"https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/{DEFAULT_ITEM_ID}"
DATA_API_BBOX_URL = "https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/{minx},{miny},{maxx},{maxy}.tif"

# Pune Historic Core Bounding Box (from STUDY_AREA_SPECIFICATION.json)
PUNE_BBOX_WGS84 = [73.840, 18.510, 73.870, 18.530]  # [minx, miny, maxx, maxy]

OUTPUT_DIR_PRIMARY = Path("data/real/india/pune/imagery/sentinel2")
OUTPUT_DIR_ALIAS = Path("data/india/pune/imagery/sentinel2")
METADATA_DIR_ALIAS = Path("data/india/pune/metadata")


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 checksum of a local file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class Sentinel2AcquisitionEngine:
    def __init__(
        self,
        item_id: str = DEFAULT_ITEM_ID,
        bbox: List[float] = PUNE_BBOX_WGS84,
        output_dir: Path = OUTPUT_DIR_PRIMARY,
        timeout_sec: int = 25,
    ):
        self.item_id = item_id
        self.bbox = bbox
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_sec = timeout_sec

    def fetch_stac_metadata(self) -> Dict[str, Any]:
        """Fetch raw STAC item metadata with explicit timeout."""
        logger.info(f"Fetching STAC metadata for item: {self.item_id}")
        url = f"https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/{self.item_id}"
        resp = requests.get(url, timeout=self.timeout_sec)
        resp.raise_for_status()
        return resp.json()

    def download_aoi_band(self, asset_name: str) -> Tuple[np.ndarray, Affine, rasterio.crs.CRS]:
        """
        Download bounded GeoTIFF for a single asset over the Pune AOI.
        Returns the data array (H, W), transform, and CRS.
        """
        minx, miny, maxx, maxy = self.bbox
        url = (
            f"https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/{minx},{miny},{maxx},{maxy}.tif"
            f"?collection=sentinel-2-l2a&item={self.item_id}&assets={asset_name}"
        )
        logger.info(f"Requesting bounded window for asset '{asset_name}' over bbox {self.bbox}...")
        resp = requests.get(url, timeout=self.timeout_sec)
        resp.raise_for_status()

        with rasterio.open(io.BytesIO(resp.content)) as src:
            data = src.read(1)  # Primary data channel
            transform = src.transform
            crs = src.crs
            logger.info(
                f"Asset '{asset_name}' retrieved successfully: shape={data.shape}, "
                f"dtype={data.dtype}, min={data.min()}, max={data.max()}"
            )
            return data, transform, crs

    def acquire_via_pystac(self) -> Dict[str, Any]:
        """
        Acquire and process Sentinel-2 L2A data using pystac and planetary-computer SDK.
        1. Loads the STAC item via pystac.Item.from_file.
        2. Signs the item using planetary_computer.sign().
        3. Opens B02, B03, B04, B08, and SCL remotely.
        4. Extracts window corresponding to the Pune AOI.
        5. Reprojects to target WGS84 grid.
        6. Generates RGB composite and NDVI.
        7. Writes files and provenance manifest.
        """
        import os
        from pyproj import Transformer
        from rasterio.transform import from_bounds
        from rasterio.warp import reproject, Resampling
        from rasterio.windows import from_bounds as win_from_bounds
        import pystac
        import planetary_computer

        os.environ["GDAL_DISABLE_READDIR_ON_OPEN"] = "EMPTY_DIR"
        os.environ["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"] = ".tif"
        os.environ["VSI_CACHE"] = "TRUE"

        logger.info(f"Loading STAC item via pystac: {STAC_API_URL}")
        item = pystac.Item.from_file(STAC_API_URL)
        logger.info("Signing STAC item with planetary_computer.sign()...")
        signed_item = planetary_computer.sign(item)

        minx, miny, maxx, maxy = self.bbox
        w10m, h10m = 324, 216
        w20m, h20m = 162, 108

        transform_10m = from_bounds(minx, miny, maxx, maxy, w10m, h10m)
        transform_20m = from_bounds(minx, miny, maxx, maxy, w20m, h20m)

        proj_transformer = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
        utm_minx, utm_miny = proj_transformer.transform(minx, miny)
        utm_maxx, utm_maxy = proj_transformer.transform(maxx, maxy)

        bands_data = {}
        band_profiles = {}
        saved_files = {}
        buffer_m = 500.0

        for asset_name in ["B02", "B03", "B04", "B08", "SCL"]:
            asset_href = signed_item.assets[asset_name].href
            logger.info(f"Opening and windowing asset '{asset_name}'...")
            with rasterio.open(asset_href) as src:
                src_crs = src.crs
                src_transform = src.transform
                win = win_from_bounds(utm_minx - buffer_m, utm_miny - buffer_m, utm_maxx + buffer_m, utm_maxy + buffer_m, src_transform)
                src_win_transform = rasterio.windows.transform(win, src_transform)
                raw_win_data = src.read(1, window=win)

                is_20m = asset_name == "SCL"
                dst_shape = (h20m, w20m) if is_20m else (h10m, w10m)
                dst_transform = transform_20m if is_20m else transform_10m
                dst_dtype = np.uint8 if is_20m else np.uint16
                dst_data = np.zeros(dst_shape, dtype=dst_dtype)

                reproject(
                    source=raw_win_data,
                    destination=dst_data,
                    src_transform=src_win_transform,
                    src_crs=src_crs,
                    dst_transform=dst_transform,
                    dst_crs="EPSG:4326",
                    resampling=Resampling.nearest if is_20m else Resampling.bilinear,
                )

                bands_data[asset_name] = dst_data
                band_profiles[asset_name] = {
                    "driver": "GTiff",
                    "dtype": dst_dtype,
                    "width": dst_shape[1],
                    "height": dst_shape[0],
                    "count": 1,
                    "crs": "EPSG:4326",
                    "transform": dst_transform,
                    "compress": "lzw",
                }

                out_path = self.output_dir / f"pune_sentinel2_{asset_name.lower()}.tif"
                with rasterio.open(out_path, "w", **band_profiles[asset_name]) as dst:
                    dst.write(dst_data, 1)
                saved_files[asset_name] = out_path

        # RGB Composite
        rgb_path = self.output_dir / "pune_sentinel2_rgb.tif"
        rgb_prof = band_profiles["B04"].copy()
        rgb_prof["count"] = 3
        with rasterio.open(rgb_path, "w", **rgb_prof) as dst:
            dst.write(bands_data["B04"], 1)
            dst.write(bands_data["B03"], 2)
            dst.write(bands_data["B02"], 3)
        saved_files["RGB"] = rgb_path

        # NDVI
        b08 = bands_data["B08"].astype(np.float32)
        b04 = bands_data["B04"].astype(np.float32)
        denom = b08 + b04
        denom[denom == 0] = 1e-8
        ndvi_data = np.clip((b08 - b04) / denom, -1.0, 1.0)
        ndvi_path = self.output_dir / "pune_sentinel2_ndvi.tif"
        ndvi_prof = band_profiles["B04"].copy()
        ndvi_prof["dtype"] = "float32"
        ndvi_prof["nodata"] = -9999.0
        with rasterio.open(ndvi_path, "w", **ndvi_prof) as dst:
            dst.write(ndvi_data.astype(np.float32), 1)
        saved_files["NDVI"] = ndvi_path

        # Mirror files
        if OUTPUT_DIR_ALIAS.resolve() != self.output_dir.resolve():
            OUTPUT_DIR_ALIAS.mkdir(parents=True, exist_ok=True)
            for k, fpath in saved_files.items():
                (OUTPUT_DIR_ALIAS / fpath.name).write_bytes(fpath.read_bytes())

        # Provenance
        file_manifest = {
            k: {
                "filename": fpath.name,
                "relative_path": str(fpath).replace("\\", "/"),
                "size_bytes": fpath.stat().st_size,
                "sha256": compute_sha256(fpath),
            }
            for k, fpath in saved_files.items()
        }

        props = item.properties
        provenance = {
            "dataset_name": "Sentinel-2 L2A Multispectral Optical Reflectance",
            "study_area_id": "pune_historic_core_pilot",
            "study_area_name": "Pune Historic Urban Core (Peth Areas), Maharashtra",
            "stac_item_id": item.id,
            "source_stac_api_url": STAC_API_URL,
            "provider": "European Space Agency (ESA) Copernicus / Microsoft Planetary Computer",
            "acquisition_datetime": props.get("datetime", "2026-10-02T05:32:41.024000Z"),
            "cloud_cover_percent": float(props.get("eo:cloud_cover", 0.6954)),
            "tile_id": ("T" + str(props.get("s2:mgrs_tile", "43QCA"))) if not str(props.get("s2:mgrs_tile", "43QCA")).startswith("T") else str(props.get("s2:mgrs_tile", "43QCA")),
            "relative_orbit": str(props.get("sat:relative_orbit", "105")),
            "source_crs": "EPSG:32643",
            "output_crs": "EPSG:4326",
            "bbox_wgs84": self.bbox,
            "raster_dimensions": {
                "height_pixels": h10m,
                "width_pixels": w10m,
                "bands_10m": 1,
                "approx_resolution_m": 10.31,
            },
            "bands_acquired": ["B02", "B03", "B04", "B08", "SCL"],
            "derived_products": ["RGB", "NDVI"],
            "scientific_usage_notice": (
                "CONTEXTUAL / LULC EVIDENCE ONLY: Sentinel-2 spatial resolution (~10m GSD) "
                "is suitable for broad vegetation, water, and urban density context. It is strictly "
                "NOT authoritative cadastral geometry and is NOT used to delineate sub-meter legal "
                "parcel boundaries."
            ),
            "processing_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "files": file_manifest,
        }

        prov_path = self.output_dir / "pune_sentinel2_provenance.json"
        prov_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
        if OUTPUT_DIR_ALIAS.resolve() != self.output_dir.resolve():
            (OUTPUT_DIR_ALIAS / "pune_sentinel2_provenance.json").write_text(
                json.dumps(provenance, indent=2), encoding="utf-8"
            )

        return provenance

    def execute_pipeline(self) -> Dict[str, Any]:
        """
        Execute full download, processing (RGB, NDVI), validation, and provenance registration.
        """
        try:
            return self.acquire_via_pystac()
        except Exception as exc:
            logger.warning(f"pystac direct window acquisition encountered {exc}, falling back to Data API bounded pipeline...")
        start_time = datetime.now(timezone.utc)
        logger.info("Starting Sentinel-2 acquisition pipeline for Pune...")


        # 1. Retrieve STAC metadata
        stac_meta = self.fetch_stac_metadata()
        properties = stac_meta.get("properties", {})
        cloud_cover = properties.get("eo:cloud_cover")
        acq_datetime = properties.get("datetime")
        source_epsg = properties.get("proj:epsg", 32643)

        # 2. Download individual bands
        bands = {}
        transforms = {}
        crss = {}

        for asset in ["B02", "B03", "B04", "B08", "SCL"]:
            try:
                arr, trans, crs_val = self.download_aoi_band(asset)
                bands[asset] = arr
                transforms[asset] = trans
                crss[asset] = crs_val
            except Exception as exc:
                logger.error(f"Failed to retrieve asset {asset}: {exc}")
                raise

        # Check reference geometry (10m bands: B02, B03, B04, B08)
        ref_shape = bands["B02"].shape
        ref_transform = transforms["B02"]
        ref_crs = crss["B02"]

        for b_name in ["B03", "B04", "B08"]:
            if bands[b_name].shape != ref_shape:
                raise ValueError(f"Band dimension mismatch: {b_name} shape {bands[b_name].shape} != {ref_shape}")

        saved_files = {}

        # 3. Save single-band GeoTIFFs
        for b_name in ["B02", "B03", "B04", "B08"]:
            out_file = self.output_dir / f"pune_sentinel2_{b_name.lower()}.tif"
            with rasterio.open(
                out_file,
                "w",
                driver="GTiff",
                height=ref_shape[0],
                width=ref_shape[1],
                count=1,
                dtype=bands[b_name].dtype,
                crs=ref_crs,
                transform=ref_transform,
            ) as dst:
                dst.write(bands[b_name], 1)
            saved_files[b_name] = out_file
            logger.info(f"Saved {b_name} to {out_file} ({out_file.stat().st_size} bytes)")

        # Save SCL (20m resolution)
        scl_file = self.output_dir / "pune_sentinel2_scl.tif"
        with rasterio.open(
            scl_file,
            "w",
            driver="GTiff",
            height=bands["SCL"].shape[0],
            width=bands["SCL"].shape[1],
            count=1,
            dtype=bands["SCL"].dtype,
            crs=crss["SCL"],
            transform=transforms["SCL"],
        ) as dst:
            dst.write(bands["SCL"], 1)
        saved_files["SCL"] = scl_file
        logger.info(f"Saved SCL to {scl_file} ({scl_file.stat().st_size} bytes)")

        # 4. Generate RGB True-Color Composite (B04=Red, B03=Green, B02=Blue)
        rgb_file = self.output_dir / "pune_sentinel2_rgb.tif"
        with rasterio.open(
            rgb_file,
            "w",
            driver="GTiff",
            height=ref_shape[0],
            width=ref_shape[1],
            count=3,
            dtype=bands["B04"].dtype,
            crs=ref_crs,
            transform=ref_transform,
        ) as dst:
            dst.write(bands["B04"], 1)  # Red
            dst.write(bands["B03"], 2)  # Green
            dst.write(bands["B02"], 3)  # Blue
        saved_files["RGB"] = rgb_file
        logger.info(f"Saved RGB composite to {rgb_file} ({rgb_file.stat().st_size} bytes)")

        # 5. Compute and Save Normalized Difference Vegetation Index (NDVI)
        # NDVI = (NIR - Red) / (NIR + Red) = (B08 - B04) / (B08 + B04)
        b08_f = bands["B08"].astype(np.float32)
        b04_f = bands["B04"].astype(np.float32)
        denom = b08_f + b04_f
        denom[denom == 0] = 1e-6
        ndvi = (b08_f - b04_f) / denom
        ndvi = np.clip(ndvi, -1.0, 1.0)

        ndvi_file = self.output_dir / "pune_sentinel2_ndvi.tif"
        with rasterio.open(
            ndvi_file,
            "w",
            driver="GTiff",
            height=ref_shape[0],
            width=ref_shape[1],
            count=1,
            dtype="float32",
            crs=ref_crs,
            transform=ref_transform,
        ) as dst:
            dst.write(ndvi.astype(np.float32), 1)
        saved_files["NDVI"] = ndvi_file
        logger.info(f"Saved NDVI to {ndvi_file} ({ndvi_file.stat().st_size} bytes, mean NDVI: {float(ndvi.mean()):.3f})")

        # 6. Copy to alias directory for path flexibility (data/india/pune/imagery/sentinel2/)
        if OUTPUT_DIR_ALIAS.resolve() != self.output_dir.resolve():
            OUTPUT_DIR_ALIAS.mkdir(parents=True, exist_ok=True)
            for k, fpath in saved_files.items():
                target = OUTPUT_DIR_ALIAS / fpath.name
                target.write_bytes(fpath.read_bytes())

        # 7. Generate Full Provenance Metadata Record
        files_metadata = {}
        for k, fpath in saved_files.items():
            files_metadata[k] = {
                "filename": fpath.name,
                "relative_path": str(fpath).replace("\\", "/"),
                "size_bytes": fpath.stat().st_size,
                "sha256": compute_sha256(fpath),
            }

        # Resolution calculation (degrees to meters approximation: ~0.0000926 deg ~ 10m)
        pixel_width_deg = abs(ref_transform.a)
        pixel_height_deg = abs(ref_transform.e)
        approx_res_m = round(pixel_width_deg * 111320.0, 2)

        provenance_manifest = {
            "dataset_name": "Sentinel-2 L2A Multispectral Optical Reflectance",
            "study_area_id": "pune_historic_core_pilot",
            "study_area_name": "Pune Historic Urban Core (Peth Areas), Maharashtra",
            "stac_item_id": self.item_id,
            "source_stac_api_url": STAC_API_URL,
            "provider": "European Space Agency (ESA) Copernicus / Microsoft Planetary Computer",
            "acquisition_datetime": acq_datetime,
            "cloud_cover_percent": round(float(cloud_cover or 0.0), 4),
            "tile_id": "T43QCA",
            "relative_orbit": "R105",
            "source_crs": f"EPSG:{source_epsg}",
            "output_crs": str(ref_crs),
            "bbox_wgs84": self.bbox,
            "raster_dimensions": {
                "height_pixels": ref_shape[0],
                "width_pixels": ref_shape[1],
                "bands_10m": 1,
                "approx_resolution_m": approx_res_m,
            },
            "bands_acquired": ["B02", "B03", "B04", "B08", "SCL"],
            "derived_products": ["RGB", "NDVI"],
            "scientific_usage_notice": (
                "CONTEXTUAL / LULC EVIDENCE ONLY: Sentinel-2 spatial resolution (~10m GSD) is suitable for "
                "broad vegetation, water, and urban density context. It is strictly NOT authoritative cadastral "
                "geometry and is NOT used to delineate sub-meter legal parcel boundaries."
            ),
            "processing_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "files": files_metadata,
        }

        # Save metadata JSON in primary and alias locations
        meta_file_primary = self.output_dir / "pune_sentinel2_provenance.json"
        meta_file_primary.write_text(json.dumps(provenance_manifest, indent=2), encoding="utf-8")
        logger.info(f"Saved provenance metadata to {meta_file_primary}")

        METADATA_DIR_ALIAS.mkdir(parents=True, exist_ok=True)
        meta_file_alias = METADATA_DIR_ALIAS / "pune_sentinel2_provenance.json"
        meta_file_alias.write_text(json.dumps(provenance_manifest, indent=2), encoding="utf-8")

        return provenance_manifest


if __name__ == "__main__":
    engine = Sentinel2AcquisitionEngine()
    manifest = engine.execute_pipeline()
    print("\n" + "=" * 70)
    print(" SENTINEL-2 PUNE ACQUISITION & INTEGRATION COMPLETE")
    print("=" * 70)
    print(f"STAC Item:        {manifest['stac_item_id']}")
    print(f"Acquisition Date: {manifest['acquisition_datetime']}")
    print(f"Cloud Cover:      {manifest['cloud_cover_percent']}%")
    print(f"Dimensions:       {manifest['raster_dimensions']['height_pixels']} x {manifest['raster_dimensions']['width_pixels']}")
    print(f"CRS:              {manifest['output_crs']}")
    print(f"Resolution:       ~{manifest['raster_dimensions']['approx_resolution_m']}m")
    print("Files Created:")
    for k, v in manifest["files"].items():
        print(f"  - {k:4s}: {v['filename']} ({v['size_bytes']:,} bytes, SHA256: {v['sha256'][:16]}...)")
