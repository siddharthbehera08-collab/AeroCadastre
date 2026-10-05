"""
AeroCadastre Road Model Training CLI.
Executes training for a given experiment configuration.
"""

import argparse
from pathlib import Path
import torch

from ml.road_detection.dataset import get_dataloaders
from ml.road_detection.trainer import RoadTrainer


def main():
    parser = argparse.ArgumentParser(description="Train AeroCadastre Road Model")
    parser.add_argument("--exp-id", type=str, required=True, help="Experiment identifier (e.g. EXP_ROAD_UNET_001)")
    parser.add_argument("--model-type", type=str, default="unet", choices=["unet", "resunet"])
    parser.add_argument("--loss-type", type=str, default="bce_dice", choices=["bce_dice", "focal_dice"])
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--base-features", type=int, default=16)
    parser.add_argument("--patch-dir", type=str, default=r"D:\SIH26012_AeroCadastre\data\real\spacenet_roads\paris\patches")
    parser.add_argument("--output-dir", type=str, default=r"D:\SIH26012_AeroCadastre\experiments\road_detection")
    
    args = parser.parse_args()
    
    patch_root = Path(args.patch_dir)
    out_root = Path(args.output_dir)
    
    print(f"Loading data from {patch_root}...")
    train_loader, val_loader, test_loader = get_dataloaders(patch_root, batch_size=args.batch_size, seed=42)
    print(f"DataLoaders ready: Train={len(train_loader.dataset)}, Val={len(val_loader.dataset)}, Test={len(test_loader.dataset)}")
    
    trainer = RoadTrainer(
        experiment_id=args.exp_id,
        output_dir=out_root,
        model_type=args.model_type,
        loss_type=args.loss_type,
        base_features=args.base_features,
        learning_rate=args.lr,
        epochs=args.epochs,
    )
    
    results = trainer.run(train_loader, val_loader)
    print("Generating validation visualizations...")
    trainer.generate_visualizations(val_loader, count=6)
    print(f"Experiment {args.exp_id} successfully completed!")


if __name__ == "__main__":
    main()
