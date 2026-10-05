"""AeroCadastre Building Segmentation Dataset & Data Augmentation.

Implements:
- AerialPatchDataset: PyTorch Dataset for on-the-fly or cached patch extraction from large aerial tiles.
- AerialAugmentation: Geospatially realistic transformations (flips, 90-deg rotations, mild color jitter).
- PatchExtractor: Grid-based sliding window patch generator with overlap and building-pixel filtering.
"""

from typing import List, Tuple, Dict, Any, Optional, Callable
import random
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset
import torchvision.transforms.functional as TF


class AerialAugmentation:
    """Geospatially realistic data augmentation for aerial imagery.

    Applies:
    - Random horizontal flip
    - Random vertical flip
    - Random 90, 180, 270 degree rotation (D4 symmetry group)
    - Mild brightness / contrast adjustments (photometric jitter)
    """

    def __init__(
        self,
        p_flip: float = 0.5,
        p_rotate: float = 0.5,
        color_jitter: bool = True,
        brightness_range: Tuple[float, float] = (0.85, 1.15),
        contrast_range: Tuple[float, float] = (0.85, 1.15),
    ):
        self.p_flip = p_flip
        self.p_rotate = p_rotate
        self.color_jitter = color_jitter
        self.brightness_range = brightness_range
        self.contrast_range = contrast_range

    def __call__(
        self, image: Image.Image, mask: Image.Image
    ) -> Tuple[Image.Image, Image.Image]:
        # Horizontal flip
        if random.random() < self.p_flip:
            image = TF.hflip(image)
            mask = TF.hflip(mask)

        # Vertical flip
        if random.random() < self.p_flip:
            image = TF.vflip(image)
            mask = TF.vflip(mask)

        # 90-degree discrete rotations
        if random.random() < self.p_rotate:
            angle = random.choice([90, 180, 270])
            image = TF.rotate(image, angle)
            mask = TF.rotate(mask, angle)

        # Mild photometric jitter on image only
        if self.color_jitter and random.random() < 0.5:
            b_factor = random.uniform(*self.brightness_range)
            c_factor = random.uniform(*self.contrast_range)
            image = TF.adjust_brightness(image, b_factor)
            image = TF.adjust_contrast(image, c_factor)

        return image, mask


class AerialPatchDataset(Dataset):
    """PyTorch Dataset yielding image patches and binary building masks.

    Supports:
    - Pre-extracted patch lists or patch coordinate manifests
    - Normalization: ImageNet mean/std or [0, 1] range
    - Augmentation pipeline for training
    """

    def __init__(
        self,
        samples: List[Dict[str, Any]],
        patch_size: int = 256,
        is_train: bool = True,
        augment: bool = True,
        normalize_imagenet: bool = True,
        cache_in_memory: bool = False,
    ):
        self.samples = samples
        self.patch_size = patch_size
        self.is_train = is_train
        self.augment = augment and is_train
        self.normalize_imagenet = normalize_imagenet
        self.cache_in_memory = cache_in_memory

        self.augmentation = AerialAugmentation() if self.augment else None

        # ImageNet statistics
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)

        self._cache: Dict[str, Image.Image] = {}

    def __len__(self) -> int:
        return len(self.samples)

    def _open_image(self, path: str) -> Image.Image:
        if self.cache_in_memory:
            if path not in self._cache:
                self._cache[path] = Image.open(path).convert("RGB")
            return self._cache[path]
        return Image.open(path).convert("RGB")

    def _open_mask(self, path: str) -> Image.Image:
        if self.cache_in_memory:
            if path not in self._cache:
                self._cache[path] = Image.open(path).convert("L")
            return self._cache[path]
        return Image.open(path).convert("L")

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        sample = self.samples[idx]

        # Case 1: Direct patch files
        if "patch_image_path" in sample and "patch_mask_path" in sample:
            img = Image.open(sample["patch_image_path"]).convert("RGB")
            msk = Image.open(sample["patch_mask_path"]).convert("L")
        # Case 2: Tile path + crop coordinates (x, y, w, h)
        elif "image_path" in sample and "crop" in sample:
            full_img = self._open_image(sample["image_path"])
            x, y, w, h = sample["crop"]
            img = full_img.crop((x, y, x + w, y + h))

            if "mask_path" in sample and sample["mask_path"]:
                full_msk = self._open_mask(sample["mask_path"])
                msk = full_msk.crop((x, y, x + w, y + h))
            else:
                msk = Image.new("L", (w, h), 0)
        else:
            raise ValueError(f"Invalid sample format: {sample}")

        # Ensure correct patch size
        if img.size != (self.patch_size, self.patch_size):
            img = img.resize((self.patch_size, self.patch_size), Image.BILINEAR)
            msk = msk.resize((self.patch_size, self.patch_size), Image.NEAREST)

        # Augmentation
        if self.augmentation is not None:
            img, msk = self.augmentation(img, msk)

        # Convert to numpy / tensors
        img_np = np.array(img, dtype=np.float32) / 255.0  # (H, W, 3)
        img_np = np.transpose(img_np, (2, 0, 1))  # (3, H, W)

        if self.normalize_imagenet:
            img_np = (img_np - self.mean) / self.std

        msk_np = np.array(msk, dtype=np.float32)
        msk_bin = (msk_np > 127.5).astype(np.float32)[None, :, :]  # (1, H, W)

        img_tensor = torch.from_numpy(img_np.copy())
        msk_tensor = torch.from_numpy(msk_bin.copy())

        return img_tensor, msk_tensor
