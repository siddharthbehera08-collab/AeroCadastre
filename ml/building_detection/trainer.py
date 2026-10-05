"""AeroCadastre Autonomous Training, Evaluation, and Improvement Pipeline.

Features:
- Full support for UNetBaseline and ResUNet architectures
- Automatic CUDA / GPU acceleration detection
- Comprehensive metrics: IoU, Dice, Precision, Recall, F1, Pixel Acc, Boundary F1
- Best checkpoint tracking based on Validation IoU
- Visual prediction grids with probability maps and overlays
- Full provenance recording (seeds, packages, hardware, config hashes)
"""

from typing import Dict, Any, List, Optional, Tuple
import os
import sys
import time
import json
import csv
import random
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ml.building_detection.models import UNetBaseline, ResUNet, BCEDiceLoss, FocalDiceLoss
from ml.building_detection.dataset import AerialPatchDataset
from ml.building_detection.metrics import compute_segmentation_metrics, compute_boundary_f1


def set_seed(seed: int = 42):
    """Ensure strict deterministic reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def get_hardware_info() -> Dict[str, Any]:
    """Inspect and record environment and hardware provenance."""
    info = {
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None (CPU)",
        "cuda_version": torch.version.cuda if torch.cuda.is_available() else "None",
        "cpu_count": os.cpu_count(),
    }
    return info


class Trainer:
    """Production Trainer for AeroCadastre Building Segmentation Models."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.experiment_id = config.get("experiment_id", "EXP_BUILDING_UNET_001")
        self.seed = config.get("seed", 42)
        set_seed(self.seed)

        self.device = torch.device("cuda" if torch.cuda.is_available() and config.get("device", "auto") != "cpu" else "cpu")
        print(f"[{self.experiment_id}] Using compute device: {self.device}")

        # Paths
        self.output_dir = Path(config.get("output_dir", f"D:/SIH26012_AeroCadastre/experiments/building_detection/{self.experiment_id}"))
        self.checkpoints_dir = self.output_dir / "checkpoints"
        self.plots_dir = self.output_dir / "plots"
        self.vis_dir = self.output_dir / "visualizations"
        self.logs_dir = self.output_dir / "logs"

        for d in [self.checkpoints_dir, self.plots_dir, self.vis_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Model instantiation
        arch = config.get("architecture", "UNetBaseline").lower()
        base_features = config.get("base_features", 32)
        if arch in ["unetbaseline", "unet"]:
            self.model = UNetBaseline(in_channels=3, out_channels=1, base_features=base_features)
        elif arch in ["resunet", "residual_unet"]:
            self.model = ResUNet(in_channels=3, out_channels=1, base_features=base_features)
        else:
            raise ValueError(f"Unknown architecture: {arch}")

        self.model.to(self.device)

        # Loss instantiation
        loss_type = config.get("loss_type", "BCEDiceLoss").lower()
        bce_weight = config.get("bce_weight", 0.5)
        if loss_type == "bcediceloss":
            self.criterion = BCEDiceLoss(bce_weight=bce_weight)
        elif loss_type == "focaldiceloss":
            self.criterion = FocalDiceLoss(focal_weight=config.get("focal_weight", 0.5))
        else:
            self.criterion = BCEDiceLoss(bce_weight=bce_weight)

        # Optimizer & Scheduler
        lr = config.get("learning_rate", 1e-3)
        weight_decay = config.get("weight_decay", 1e-4)
        opt_name = config.get("optimizer", "AdamW").lower()
        if opt_name == "adamw":
            self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=weight_decay)
        elif opt_name == "sgd":
            self.optimizer = torch.optim.SGD(self.model.parameters(), lr=lr, momentum=0.9, weight_decay=weight_decay)
        else:
            self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr, weight_decay=weight_decay)

        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode="max", factor=0.5, patience=2
        )

        self.best_val_iou = 0.0
        self.history: List[Dict[str, Any]] = []

    def train_epoch(self, dataloader: DataLoader) -> Tuple[float, Dict[str, float]]:
        self.model.train()
        total_loss = 0.0
        all_probs, all_targets = [], []

        for batch_idx, (images, masks) in enumerate(dataloader):
            images = images.to(self.device)
            masks = masks.to(self.device)

            self.optimizer.zero_grad()
            logits = self.model(images)
            loss = self.criterion(logits, masks)
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()

            probs = torch.sigmoid(logits).detach().cpu().numpy()
            targets = masks.detach().cpu().numpy()

            all_probs.append(probs)
            all_targets.append(targets)

        avg_loss = total_loss / max(1, len(dataloader))
        concat_probs = np.concatenate(all_probs, axis=0)
        concat_targets = np.concatenate(all_targets, axis=0)
        metrics = compute_segmentation_metrics(concat_probs, concat_targets, threshold=0.5, compute_boundary=False)
        metrics["loss"] = round(avg_loss, 4)
        return avg_loss, metrics

    def validate(self, dataloader: DataLoader, compute_boundary: bool = True) -> Tuple[float, Dict[str, float]]:
        self.model.eval()
        total_loss = 0.0
        all_probs, all_targets = [], []

        with torch.no_grad():
            for images, masks in dataloader:
                images = images.to(self.device)
                masks = masks.to(self.device)

                logits = self.model(images)
                loss = self.criterion(logits, masks)
                total_loss += loss.item()

                probs = torch.sigmoid(logits).detach().cpu().numpy()
                targets = masks.detach().cpu().numpy()

                all_probs.append(probs)
                all_targets.append(targets)

        avg_loss = total_loss / max(1, len(dataloader))
        concat_probs = np.concatenate(all_probs, axis=0)
        concat_targets = np.concatenate(all_targets, axis=0)
        metrics = compute_segmentation_metrics(concat_probs, concat_targets, threshold=0.5, compute_boundary=compute_boundary)
        metrics["loss"] = round(avg_loss, 4)
        return avg_loss, metrics

    def run(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        epochs: int = 10,
        smoke_test: bool = False,
    ) -> Dict[str, Any]:
        """Execute the complete training and validation cycle."""
        print(f"\n=======================================================")
        print(f"Starting Training: {self.experiment_id} | Epochs: {epochs} | Device: {self.device}")
        print(f"=======================================================")

        if smoke_test:
            epochs = 1
            print("Running in SMOKE-TEST mode (1 epoch, minimal validation)...")

        start_time = time.time()

        for epoch in range(1, epochs + 1):
            ep_start = time.time()

            train_loss, train_metrics = self.train_epoch(train_loader)
            val_loss, val_metrics = self.validate(val_loader, compute_boundary=(epoch == epochs or epoch % 2 == 0))

            ep_duration = time.time() - ep_start
            current_lr = self.optimizer.param_groups[0]["lr"]

            # Step scheduler based on validation IoU
            self.scheduler.step(val_metrics["iou"])

            # Check if best model
            is_best = val_metrics["iou"] > self.best_val_iou
            if is_best:
                self.best_val_iou = val_metrics["iou"]
                self.save_checkpoint("best_model.pt", epoch, val_metrics)

            self.save_checkpoint("last_model.pt", epoch, val_metrics)

            record = {
                "epoch": epoch,
                "duration_sec": round(ep_duration, 2),
                "lr": current_lr,
                "train_loss": train_metrics["loss"],
                "train_iou": train_metrics["iou"],
                "train_dice": train_metrics["dice"],
                "val_loss": val_metrics["loss"],
                "val_iou": val_metrics["iou"],
                "val_dice": val_metrics["dice"],
                "val_precision": val_metrics["precision"],
                "val_recall": val_metrics["recall"],
                "val_pixel_accuracy": val_metrics["pixel_accuracy"],
                "val_boundary_f1": val_metrics.get("boundary_f1", 0.0),
            }
            self.history.append(record)

            print(
                f"Epoch [{epoch:02d}/{epochs:02d}] "
                f"Train Loss: {train_loss:.4f}, IoU: {train_metrics['iou']:.4f} | "
                f"Val Loss: {val_loss:.4f}, IoU: {val_metrics['iou']:.4f}, Dice: {val_metrics['dice']:.4f}, "
                f"Boundary F1: {val_metrics.get('boundary_f1', 0.0):.4f} "
                f"[{ep_duration:.1f}s]"
                f"{' *BEST*' if is_best else ''}",
                flush=True,
            )
            self.save_history()

        total_time = time.time() - start_time
        print(f"\nTraining completed in {total_time:.1f}s. Best Val IoU: {self.best_val_iou:.4f}", flush=True)

        from ml.building_detection.registry import register_model
        register_model(
            experiment_id=self.experiment_id,
            checkpoint_path=self.checkpoints_dir / "best_model.pt",
            architecture=self.config.get("architecture", "UNetBaseline"),
            metrics=self.history[-1] if self.history else {},
            config=self.config,
            status="candidate",
        )

        # Save training history & plots
        self.save_history()
        self.generate_plots()
        self.generate_visualizations(val_loader)
        self.save_provenance(total_time)

        return {
            "experiment_id": self.experiment_id,
            "best_val_iou": self.best_val_iou,
            "history": self.history,
            "final_val_metrics": self.history[-1] if self.history else {},
        }

    def save_checkpoint(self, filename: str, epoch: int, metrics: Dict[str, Any]):
        ckpt_path = self.checkpoints_dir / filename
        torch.save({
            "epoch": epoch,
            "experiment_id": self.experiment_id,
            "architecture": self.config.get("architecture", "UNetBaseline"),
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "config": self.config,
            "metrics": metrics,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }, ckpt_path)

    def save_history(self):
        csv_path = self.output_dir / "training_history.csv"
        if self.history:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(self.history[0].keys()))
                writer.writeheader()
                writer.writerows(self.history)

        json_path = self.output_dir / "metrics.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "experiment_id": self.experiment_id,
                "best_val_iou": self.best_val_iou,
                "history": self.history,
            }, f, indent=2)

    def generate_plots(self):
        if not self.history:
            return
        epochs = [h["epoch"] for h in self.history]
        t_loss = [h["train_loss"] for h in self.history]
        v_loss = [h["val_loss"] for h in self.history]
        v_iou = [h["val_iou"] for h in self.history]
        v_dice = [h["val_dice"] for h in self.history]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # Loss curve
        ax1.plot(epochs, t_loss, label="Train Loss", color="royalblue", lw=2)
        ax1.plot(epochs, v_loss, label="Val Loss", color="crimson", lw=2)
        ax1.set_title(f"{self.experiment_id} — Loss Convergence")
        ax1.set_xlabel("Epoch")
        ax1.set_ylabel("Total Loss")
        ax1.grid(True, linestyle="--", alpha=0.5)
        ax1.legend()

        # Metrics curve
        ax2.plot(epochs, v_iou, label="Val IoU (Jaccard)", color="forestgreen", lw=2)
        ax2.plot(epochs, v_dice, label="Val Dice (F1)", color="darkorange", lw=2)
        if "val_boundary_f1" in self.history[0]:
            v_b_f1 = [h.get("val_boundary_f1", 0.0) for h in self.history]
            ax2.plot(epochs, v_b_f1, label="Val Boundary F1", color="purple", lw=2, linestyle=":")
        ax2.set_title(f"{self.experiment_id} — Validation Metrics")
        ax2.set_xlabel("Epoch")
        ax2.set_ylabel("Metric Score")
        ax2.set_ylim(0, 1.05)
        ax2.grid(True, linestyle="--", alpha=0.5)
        ax2.legend()

        plt.tight_layout()
        plt.savefig(self.plots_dir / "training_curves.png", dpi=150)
        plt.close(fig)

    def generate_visualizations(self, dataloader: DataLoader, max_samples: int = 6):
        """Generate high-resolution visual predictions: Image, GT Mask, Prob Map, Binary Mask, Overlay."""
        self.model.eval()
        count = 0

        # Mean/std for un-normalizing
        mean = np.array([0.485, 0.456, 0.406]).reshape(3, 1, 1)
        std = np.array([0.229, 0.224, 0.225]).reshape(3, 1, 1)

        with torch.no_grad():
            for images, masks in dataloader:
                images = images.to(self.device)
                logits = self.model(images)
                probs = torch.sigmoid(logits).cpu().numpy()

                for i in range(images.size(0)):
                    if count >= max_samples:
                        return
                    img_np = images[i].cpu().numpy()
                    img_unnorm = np.clip((img_np * std + mean).transpose(1, 2, 0), 0.0, 1.0)

                    gt_mask = masks[i, 0].cpu().numpy()
                    prob_map = probs[i, 0]
                    bin_mask = (prob_map >= 0.5).astype(np.float32)

                    # Create 5-panel comparison figure
                    fig, axes = plt.subplots(1, 5, figsize=(20, 4))
                    axes[0].imshow(img_unnorm)
                    axes[0].set_title("Aerial RGB")
                    axes[0].axis("off")

                    axes[1].imshow(gt_mask, cmap="gray")
                    axes[1].set_title("Ground Truth Mask")
                    axes[1].axis("off")

                    im_prob = axes[2].imshow(prob_map, cmap="jet", vmin=0, vmax=1)
                    axes[2].set_title("Predicted Probability")
                    axes[2].axis("off")
                    plt.colorbar(im_prob, ax=axes[2], fraction=0.046, pad=0.04)

                    axes[3].imshow(bin_mask, cmap="gray")
                    axes[3].set_title("Binary Mask (thr=0.5)")
                    axes[3].axis("off")

                    # Overlay
                    overlay = img_unnorm.copy()
                    # Green = TP, Red = FP, Blue = FN
                    tp = (bin_mask == 1) & (gt_mask == 1)
                    fp = (bin_mask == 1) & (gt_mask == 0)
                    fn = (bin_mask == 0) & (gt_mask == 1)

                    overlay[tp] = overlay[tp] * 0.5 + np.array([0.0, 0.8, 0.0]) * 0.5
                    overlay[fp] = overlay[fp] * 0.5 + np.array([0.9, 0.0, 0.0]) * 0.5
                    overlay[fn] = overlay[fn] * 0.5 + np.array([0.0, 0.2, 0.9]) * 0.5

                    axes[4].imshow(np.clip(overlay, 0.0, 1.0))
                    axes[4].set_title("Error Overlay (G=TP, R=FP, B=FN)")
                    axes[4].axis("off")

                    plt.tight_layout()
                    plt.savefig(self.vis_dir / f"val_sample_{count + 1:02d}.png", dpi=150)
                    plt.close(fig)

                    count += 1

    def save_provenance(self, total_time: float):
        prov = {
            "experiment_id": self.experiment_id,
            "architecture": self.config.get("architecture", "UNetBaseline"),
            "dataset": "Inria Aerial Image Labeling Benchmark",
            "seed": self.seed,
            "total_training_time_sec": round(total_time, 2),
            "best_val_iou": round(self.best_val_iou, 4),
            "hardware": get_hardware_info(),
            "config": self.config,
            "config_hash": hashlib.sha256(json.dumps(self.config, sort_keys=True).encode()).hexdigest(),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with open(self.output_dir / "model_metadata.json", "w", encoding="utf-8") as f:
            json.dump(prov, f, indent=2)
