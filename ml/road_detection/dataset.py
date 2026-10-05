"""
AeroCadastre Road Segmentation Dataset & Augmentation Engine.
Loads aerial RGB image patches and binary road masks with deterministic seeding and augmentations.
"""

import os
import random
from pathlib import Path
from typing import Tuple, List, Optional, Callable

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image


class RoadPatchDataset(Dataset):
    """
    PyTorch Dataset for binary road segmentation from satellite/aerial imagery.
    
    Classes:
        0 = Background
        1 = Road
    """
    def __init__(
        self,
        patch_dir: Path,
        split: str = "train",
        augment: bool = False,
        normalize: bool = True,
    ):
        self.split = split
        self.augment = augment
        self.normalize = normalize
        
        self.images_dir = patch_dir / split / "images"
        self.masks_dir = patch_dir / split / "masks"
        
        if not self.images_dir.exists():
            raise FileNotFoundError(f"Images directory not found: {self.images_dir}")
        if not self.masks_dir.exists():
            raise FileNotFoundError(f"Masks directory not found: {self.masks_dir}")
            
        self.filenames = sorted([f.name for f in self.images_dir.glob("*.png")])
        if len(self.filenames) == 0:
            raise ValueError(f"No PNG patches found in {self.images_dir}")
            
        # Standard satellite / ImageNet normalization parameters
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)

    def __len__(self) -> int:
        return len(self.filenames)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        fname = self.filenames[idx]
        img_path = self.images_dir / fname
        mask_path = self.masks_dir / fname
        
        # Load image (RGB)
        img = Image.open(img_path).convert("RGB")
        img_np = np.array(img, dtype=np.float32) / 255.0  # (H, W, 3), [0, 1]
        
        # Load mask (binary)
        mask = Image.open(mask_path).convert("L")
        mask_np = np.array(mask, dtype=np.float32)
        mask_np = (mask_np > 127).astype(np.float32)  # (H, W), values {0.0, 1.0}
        
        if self.augment:
            img_np, mask_np = self._apply_augmentations(img_np, mask_np)
            
        # Transpose image to (C, H, W)
        img_tensor = np.transpose(img_np, (2, 0, 1))
        
        if self.normalize:
            img_tensor = (img_tensor - self.mean) / self.std
            
        mask_tensor = mask_np[np.newaxis, :, :]  # (1, H, W)
        
        return (
            torch.from_numpy(img_tensor).float(),
            torch.from_numpy(mask_tensor).float(),
        )

    def _apply_augmentations(
        self, img: np.ndarray, mask: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Apply geometric and radiometric augmentations preserving linear continuity."""
        # 1. Random horizontal flip
        if random.random() > 0.5:
            img = np.fliplr(img).copy()
            mask = np.fliplr(mask).copy()
            
        # 2. Random vertical flip
        if random.random() > 0.5:
            img = np.flipud(img).copy()
            mask = np.flipud(mask).copy()
            
        # 3. Random 90-degree rotations
        rot_k = random.choice([0, 1, 2, 3])
        if rot_k > 0:
            img = np.rot90(img, k=rot_k).copy()
            mask = np.rot90(mask, k=rot_k).copy()
            
        # 4. Mild photometric jitter (brightness & contrast)
        if random.random() > 0.5:
            alpha = random.uniform(0.85, 1.15)  # contrast
            beta = random.uniform(-0.1, 0.1)    # brightness
            img = np.clip(img * alpha + beta, 0.0, 1.0)
            
        return img, mask


def get_dataloaders(
    patch_root: Path,
    batch_size: int = 8,
    num_workers: int = 0,
    seed: int = 42,
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """Create deterministic DataLoaders for train, val, and test splits."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    
    train_ds = RoadPatchDataset(patch_root, split="train", augment=True)
    val_ds = RoadPatchDataset(patch_root, split="val", augment=False)
    test_ds = RoadPatchDataset(patch_root, split="test", augment=False)
    
    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=False,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=False,
    )
    test_loader = DataLoader(
        test_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=False,
    )
    
    return train_loader, val_loader, test_loader
