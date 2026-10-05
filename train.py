"""AeroCadastre Building Detection Model Training Runner CLI.

Usage:
    python train.py --config experiments/building_detection/configs/EXP_BUILDING_UNET_001.yaml [--smoke-test]
"""

import argparse
import json
from pathlib import Path
import yaml
import torch
from torch.utils.data import DataLoader

from ml.building_detection.trainer import Trainer, set_seed
from ml.building_detection.dataset import AerialPatchDataset
from ml.building_detection.validation import validate_dataset_pairs
from ml.building_detection.splitter import create_geographic_splits
from ml.building_detection.patch_extractor import generate_patch_manifest


def load_config(config_path: Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def prepare_manifests_if_needed(config: dict) -> Path:
    """Ensure validation, split, and patch manifests exist."""
    exported_manifest = Path("D:/SIH26012_AeroCadastre/data/real/inria/patches/exported_patch_manifest.json")
    if exported_manifest.exists():
        return exported_manifest

    root_dir = Path(config["dataset"]["root_dir"])
    manifest_dir = Path("D:/SIH26012_AeroCadastre/experiments/building_detection/manifests")
    manifest_dir.mkdir(parents=True, exist_ok=True)

    split_manifest_path = manifest_dir / "split_manifest.json"
    patch_manifest_path = manifest_dir / "patch_manifest.json"

    if not split_manifest_path.exists():
        print("Split manifest not found. Running validation and geographic splitting...")
        val_res = validate_dataset_pairs(root_dir, manifest_dir)
        create_geographic_splits(val_res["valid_pairs"], manifest_dir)

    if not patch_manifest_path.exists():
        print("Patch manifest not found. Extracting patch coordinates...")
        patch_size = config["dataset"].get("patch_size", 256)
        stride = config["dataset"].get("stride", 256)
        generate_patch_manifest(
            split_manifest_path=split_manifest_path,
            output_dir=manifest_dir,
            patch_size=patch_size,
            stride=stride,
            min_building_ratio=0.005,
            max_bg_ratio=0.30,
            seed=config.get("seed", 42),
        )

    return patch_manifest_path


def main():
    parser = argparse.ArgumentParser(description="AeroCadastre Building Detection Training")
    parser.add_argument("--config", required=True, type=Path, help="Path to experiment YAML configuration")
    parser.add_argument("--smoke-test", action="store_true", help="Run in smoke-test mode (1 epoch, minimal batches)")
    parser.add_argument("--epochs", type=int, default=None, help="Override number of training epochs")
    parser.add_argument("--batch-size", type=int, default=None, help="Override batch size")
    parser.add_argument("--num-workers", type=int, default=0, help="DataLoader worker processes")

    args = parser.parse_args()
    config = load_config(args.config)

    if args.epochs is not None:
        config["training"]["epochs"] = args.epochs
    if args.batch_size is not None:
        config["training"]["batch_size"] = args.batch_size

    set_seed(config.get("seed", 42))

    # Ensure manifests exist
    patch_manifest_path = prepare_manifests_if_needed(config)
    with open(patch_manifest_path, "r", encoding="utf-8") as f:
        patch_data = json.load(f)

    train_patches = patch_data["patches"]["train"]
    val_patches = patch_data["patches"]["val"]

    if args.smoke_test:
        train_patches = train_patches[:32]
        val_patches = val_patches[:16]
    else:
        max_train = config.get("training", {}).get("max_train_samples")
        if max_train:
            train_patches = train_patches[:max_train]
        max_val = config.get("training", {}).get("max_val_samples")
        if max_val:
            val_patches = val_patches[:max_val]

    print(f"Loaded {len(train_patches)} training patches, {len(val_patches)} validation patches.", flush=True)

    patch_size = config["dataset"].get("patch_size", 256)
    train_dataset = AerialPatchDataset(
        samples=train_patches,
        patch_size=patch_size,
        is_train=True,
        augment=config.get("augmentation", {}).get("hflip", True),
        normalize_imagenet=config["dataset"].get("normalize_imagenet", True),
    )

    val_dataset = AerialPatchDataset(
        samples=val_patches,
        patch_size=patch_size,
        is_train=False,
        augment=False,
        normalize_imagenet=config["dataset"].get("normalize_imagenet", True),
    )

    batch_size = config["training"].get("batch_size", 16)
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    trainer = Trainer(config)
    results = trainer.run(
        train_loader=train_loader,
        val_loader=val_loader,
        epochs=config["training"].get("epochs", 8),
        smoke_test=args.smoke_test,
    )

    print("\nTraining completed successfully:")
    print(f"Experiment ID: {results['experiment_id']}")
    print(f"Best Val IoU: {results['best_val_iou']:.4f}")


if __name__ == "__main__":
    main()
