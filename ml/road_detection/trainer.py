"""
AeroCadastre Road Model Trainer & Experiment Engine.
Executes training loops, metric logging, checkpointing, and validation visualizations.
"""

import os
import time
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from PIL import Image

from ml.road_detection.models import RoadUNetBaseline, RoadResUNet, BCEDiceLoss, FocalDiceLoss
from ml.road_detection.metrics import compute_segmentation_metrics, compute_road_connectivity_metrics


class RoadTrainer:
    """End-to-end training and evaluation manager for road detection experiments."""
    
    def __init__(
        self,
        experiment_id: str,
        output_dir: Path,
        model_type: str = "unet",
        loss_type: str = "bce_dice",
        base_features: int = 16,
        learning_rate: float = 1e-3,
        epochs: int = 5,
        device: Optional[torch.device] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ):
        self.experiment_id = experiment_id
        self.exp_dir = output_dir / experiment_id
        self.checkpoints_dir = self.exp_dir / "checkpoints"
        self.plots_dir = self.exp_dir / "plots"
        self.viz_dir = self.exp_dir / "visualizations"
        
        for d in [self.checkpoints_dir, self.plots_dir, self.viz_dir]:
            d.mkdir(parents=True, exist_ok=True)
            
        self.epochs = epochs
        self.lr = learning_rate
        self.model_type = model_type.lower()
        self.loss_type = loss_type.lower()
        self.base_features = base_features
        
        # Setup device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = device
            
        # Instantiate Model
        if self.model_type == "resunet":
            self.model = RoadResUNet(in_channels=3, out_channels=1, base_features=base_features)
        else:
            self.model = RoadUNetBaseline(in_channels=3, out_channels=1, base_features=base_features)
        self.model.to(self.device)
        
        # Instantiate Loss
        if self.loss_type == "focal_dice":
            self.criterion = FocalDiceLoss()
        else:
            self.criterion = BCEDiceLoss()
            
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr, weight_decay=1e-5)
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(self.optimizer, mode="max", factor=0.5, patience=2)
        
        self.history = []
        self.best_val_iou = 0.0
        
        # Save training config
        self.config = {
            "experiment_id": self.experiment_id,
            "model_type": self.model_type,
            "loss_type": self.loss_type,
            "base_features": self.base_features,
            "epochs": self.epochs,
            "learning_rate": self.lr,
            "device": str(self.device),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if config_overrides:
            self.config.update(config_overrides)
            
        with open(self.exp_dir / "training_config.yaml", "w") as f:
            yaml.dump(self.config, f)

    def train_epoch(self, dataloader: DataLoader) -> Dict[str, float]:
        self.model.train()
        total_loss = 0.0
        all_preds = []
        all_targets = []
        
        for images, masks in dataloader:
            images = images.to(self.device)
            masks = masks.to(self.device)
            
            self.optimizer.zero_grad()
            logits = self.model(images)
            loss = self.criterion(logits, masks)
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item() * images.size(0)
            
            probs = torch.sigmoid(logits).detach().cpu().numpy()
            all_preds.append(probs)
            all_targets.append(masks.detach().cpu().numpy())
            
        avg_loss = total_loss / len(dataloader.dataset)
        preds_np = np.concatenate(all_preds, axis=0)
        targets_np = np.concatenate(all_targets, axis=0)
        metrics = compute_segmentation_metrics(preds_np, targets_np)
        metrics["loss"] = avg_loss
        return metrics

    def validate_epoch(self, dataloader: DataLoader) -> Tuple[Dict[str, float], Dict[str, float]]:
        self.model.eval()
        total_loss = 0.0
        all_preds = []
        all_targets = []
        
        with torch.no_grad():
            for images, masks in dataloader:
                images = images.to(self.device)
                masks = masks.to(self.device)
                
                logits = self.model(images)
                loss = self.criterion(logits, masks)
                total_loss += loss.item() * images.size(0)
                
                probs = torch.sigmoid(logits).cpu().numpy()
                all_preds.append(probs)
                all_targets.append(masks.cpu().numpy())
                
        avg_loss = total_loss / len(dataloader.dataset)
        preds_np = np.concatenate(all_preds, axis=0)
        targets_np = np.concatenate(all_targets, axis=0)
        
        seg_metrics = compute_segmentation_metrics(preds_np, targets_np)
        seg_metrics["loss"] = avg_loss
        
        # Sample connectivity on subset
        conn_metrics = compute_road_connectivity_metrics(preds_np[:10, 0] > 0.5, targets_np[:10, 0] > 0.5)
        
        return seg_metrics, conn_metrics

    def run(self, train_loader: DataLoader, val_loader: DataLoader) -> Dict[str, Any]:
        print(f"=== Starting Training for {self.experiment_id} ({self.epochs} epochs on {self.device}) ===")
        
        for epoch in range(1, self.epochs + 1):
            t0 = time.time()
            train_metrics = self.train_epoch(train_loader)
            val_metrics, conn_metrics = self.validate_epoch(val_loader)
            duration = round(time.time() - t0, 2)
            
            current_lr = self.optimizer.param_groups[0]["lr"]
            self.scheduler.step(val_metrics["iou"])
            
            record = {
                "epoch": epoch,
                "duration_sec": duration,
                "lr": current_lr,
                "train_loss": round(train_metrics["loss"], 4),
                "train_iou": round(train_metrics["iou"], 4),
                "train_dice": round(train_metrics["dice"], 4),
                "val_loss": round(val_metrics["loss"], 4),
                "val_iou": round(val_metrics["iou"], 4),
                "val_dice": round(val_metrics["dice"], 4),
                "val_precision": round(val_metrics["precision"], 4),
                "val_recall": round(val_metrics["recall"], 4),
                "val_pixel_accuracy": round(val_metrics["pixel_accuracy"], 4),
                "val_connectivity_coverage": conn_metrics["centerline_coverage"],
                "val_fragmentation_index": conn_metrics["fragmentation_index"],
            }
            self.history.append(record)
            
            print(
                f"Epoch {epoch:02d}/{self.epochs:02d} [{duration:.1f}s] | "
                f"Train Loss: {record['train_loss']:.4f}, IoU: {record['train_iou']:.4f} | "
                f"Val Loss: {record['val_loss']:.4f}, IoU: {record['val_iou']:.4f}, Dice: {record['val_dice']:.4f}, "
                f"Conn: {record['val_connectivity_coverage']:.3f}"
            )
            
            # Save last checkpoint
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": self.model.state_dict(),
                    "optimizer_state_dict": self.optimizer.state_dict(),
                    "architecture": self.model.__class__.__name__,
                    "config": self.config,
                },
                self.checkpoints_dir / "last_model.pth",
            )
            
            # Save best checkpoint
            if val_metrics["iou"] > self.best_val_iou:
                self.best_val_iou = val_metrics["iou"]
                torch.save(
                    {
                        "epoch": epoch,
                        "model_state_dict": self.model.state_dict(),
                        "optimizer_state_dict": self.optimizer.state_dict(),
                        "architecture": self.model.__class__.__name__,
                        "config": self.config,
                        "val_metrics": val_metrics,
                    },
                    self.checkpoints_dir / "best_model.pth",
                )
                
        # Save training history
        df_hist = pd.DataFrame(self.history)
        df_hist.to_csv(self.exp_dir / "training_history.csv", index=False)
        df_hist.to_csv(self.exp_dir / "metrics.csv", index=False)
        
        final_metrics = self.history[-1]
        with open(self.exp_dir / "metrics.json", "w") as f:
            json.dump(final_metrics, f, indent=2)
            
        print(f"Training completed! Best Val IoU: {self.best_val_iou:.4f}")
        return final_metrics

    def generate_visualizations(self, dataloader: DataLoader, count: int = 6):
        """Save input, ground-truth, probability map, and overlay for sample validation patches."""
        self.model.eval()
        saved = 0
        mean = np.array([0.485, 0.456, 0.406]).reshape(3, 1, 1)
        std = np.array([0.229, 0.224, 0.225]).reshape(3, 1, 1)
        
        with torch.no_grad():
            for images, masks in dataloader:
                images_dev = images.to(self.device)
                logits = self.model(images_dev)
                probs = torch.sigmoid(logits).cpu().numpy()
                
                for i in range(images.size(0)):
                    if saved >= count:
                        return
                    # Denormalize image
                    img_np = images[i].numpy() * std + mean
                    img_np = np.clip(img_np * 255.0, 0, 255).astype(np.uint8)
                    img_rgb = np.transpose(img_np, (1, 2, 0))
                    
                    gt_mask = (masks[i, 0].numpy() * 255.0).astype(np.uint8)
                    prob_map = (probs[i, 0] * 255.0).astype(np.uint8)
                    bin_pred = ((probs[i, 0] >= 0.5) * 255.0).astype(np.uint8)
                    
                    # Create 4-panel comparison canvas
                    h, w = img_rgb.shape[:2]
                    canvas = np.zeros((h, w * 4, 3), dtype=np.uint8)
                    canvas[:, :w] = img_rgb
                    canvas[:, w:w*2] = np.stack([gt_mask]*3, axis=-1)
                    canvas[:, w*2:w*3] = np.stack([prob_map]*3, axis=-1)
                    
                    # Overlay: green road prediction over RGB
                    overlay = img_rgb.copy()
                    pred_road = bin_pred > 0
                    overlay[pred_road] = [0, 255, 0]
                    blended = (0.6 * img_rgb + 0.4 * overlay).astype(np.uint8)
                    canvas[:, w*3:] = blended
                    
                    out_path = self.viz_dir / f"val_sample_{saved+1:02d}.png"
                    Image.fromarray(canvas).save(out_path)
                    saved += 1
