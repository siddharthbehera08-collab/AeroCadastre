"""
AeroCadastre Road Segmentation Neural Architectures & Loss Formulations.
Provides Compact U-Net baseline and Residual U-Net (ResUNet) for thin linear feature extraction.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


# ==============================================================================
# 1. Compact U-Net Baseline Architecture
# ==============================================================================

class DoubleConv(nn.Module):
    """Standard double convolution block: (Conv -> BN -> ReLU) * 2."""
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(x)


class RoadUNetBaseline(nn.Module):
    """
    Compact U-Net architecture optimized for binary road segmentation.
    Base feature channels = 16 (yielding ~1.94M parameters, ideal for fast CPU/GPU training).
    """
    def __init__(self, in_channels: int = 3, out_channels: int = 1, base_features: int = 16):
        super().__init__()
        f = base_features
        
        # Encoder
        self.enc1 = DoubleConv(in_channels, f)
        self.pool1 = nn.MaxPool2d(2)
        
        self.enc2 = DoubleConv(f, f * 2)
        self.pool2 = nn.MaxPool2d(2)
        
        self.enc3 = DoubleConv(f * 2, f * 4)
        self.pool3 = nn.MaxPool2d(2)
        
        self.enc4 = DoubleConv(f * 4, f * 8)
        self.pool4 = nn.MaxPool2d(2)
        
        # Bottleneck
        self.bottleneck = DoubleConv(f * 8, f * 16)
        
        # Decoder
        self.up4 = nn.ConvTranspose2d(f * 16, f * 8, kernel_size=2, stride=2)
        self.dec4 = DoubleConv(f * 16, f * 8)
        
        self.up3 = nn.ConvTranspose2d(f * 8, f * 4, kernel_size=2, stride=2)
        self.dec3 = DoubleConv(f * 8, f * 4)
        
        self.up2 = nn.ConvTranspose2d(f * 4, f * 2, kernel_size=2, stride=2)
        self.dec2 = DoubleConv(f * 4, f * 2)
        
        self.up1 = nn.ConvTranspose2d(f * 2, f, kernel_size=2, stride=2)
        self.dec1 = DoubleConv(f * 2, f)
        
        self.final_conv = nn.Conv2d(f, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool1(e1))
        e3 = self.enc3(self.pool2(e2))
        e4 = self.enc4(self.pool3(e3))
        
        b = self.bottleneck(self.pool4(e4))
        
        d4 = self.dec4(torch.cat([self.up4(b), e4], dim=1))
        d3 = self.dec3(torch.cat([self.up3(d4), e3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        
        return self.final_conv(d1)


# ==============================================================================
# 2. Residual U-Net (ResUNet) for Superior Linear Connectivity
# ==============================================================================

class ResidualConvBlock(nn.Module):
    """Residual convolution block with identity skip connection."""
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
        )
        self.shortcut = (
            nn.Sequential(
                nn.Conv2d(in_ch, out_ch, kernel_size=1, bias=False),
                nn.BatchNorm2d(out_ch),
            )
            if in_ch != out_ch
            else nn.Identity()
        )
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = self.shortcut(x)
        out = self.conv(x)
        return self.relu(out + res)


class RoadResUNet(nn.Module):
    """
    Residual U-Net architecture preserving high-frequency road edge gradients.
    """
    def __init__(self, in_channels: int = 3, out_channels: int = 1, base_features: int = 16):
        super().__init__()
        f = base_features
        
        self.enc1 = ResidualConvBlock(in_channels, f)
        self.pool1 = nn.MaxPool2d(2)
        
        self.enc2 = ResidualConvBlock(f, f * 2)
        self.pool2 = nn.MaxPool2d(2)
        
        self.enc3 = ResidualConvBlock(f * 2, f * 4)
        self.pool3 = nn.MaxPool2d(2)
        
        self.enc4 = ResidualConvBlock(f * 4, f * 8)
        self.pool4 = nn.MaxPool2d(2)
        
        self.bottleneck = ResidualConvBlock(f * 8, f * 16)
        
        self.up4 = nn.ConvTranspose2d(f * 16, f * 8, kernel_size=2, stride=2)
        self.dec4 = ResidualConvBlock(f * 16, f * 8)
        
        self.up3 = nn.ConvTranspose2d(f * 8, f * 4, kernel_size=2, stride=2)
        self.dec3 = ResidualConvBlock(f * 8, f * 4)
        
        self.up2 = nn.ConvTranspose2d(f * 4, f * 2, kernel_size=2, stride=2)
        self.dec2 = ResidualConvBlock(f * 4, f * 2)
        
        self.up1 = nn.ConvTranspose2d(f * 2, f, kernel_size=2, stride=2)
        self.dec1 = ResidualConvBlock(f * 2, f)
        
        self.final_conv = nn.Conv2d(f, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool1(e1))
        e3 = self.enc3(self.pool2(e2))
        e4 = self.enc4(self.pool3(e3))
        
        b = self.bottleneck(self.pool4(e4))
        
        d4 = self.dec4(torch.cat([self.up4(b), e4], dim=1))
        d3 = self.dec3(torch.cat([self.up3(d4), e3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        
        return self.final_conv(d1)


# ==============================================================================
# 3. Loss Formulations
# ==============================================================================

class BCEDiceLoss(nn.Module):
    """Weighted combination of Binary Cross-Entropy and Soft Dice Loss."""
    def __init__(self, bce_weight: float = 0.5, dice_weight: float = 0.5, smooth: float = 1e-6):
        super().__init__()
        self.bce_weight = bce_weight
        self.dice_weight = dice_weight
        self.smooth = smooth
        self.bce = nn.BCEWithLogitsLoss()

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce_loss = self.bce(logits, targets)
        
        probs = torch.sigmoid(logits)
        probs_flat = probs.view(-1)
        targets_flat = targets.view(-1)
        
        intersection = (probs_flat * targets_flat).sum()
        dice = (2.0 * intersection + self.smooth) / (
            probs_flat.sum() + targets_flat.sum() + self.smooth
        )
        dice_loss = 1.0 - dice
        
        return self.bce_weight * bce_loss + self.dice_weight * dice_loss


class FocalDiceLoss(nn.Module):
    """
    Focal Loss + Dice Loss specifically mitigating extreme 1:50 class imbalance in roads.
    """
    def __init__(self, alpha: float = 0.25, gamma: float = 2.0, dice_weight: float = 0.5, smooth: float = 1e-6):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.dice_weight = dice_weight
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        probs = torch.sigmoid(logits)
        bce = F.binary_cross_entropy_with_logits(logits, targets, reduction="none")
        
        p_t = probs * targets + (1.0 - probs) * (1.0 - targets)
        focal_factor = (1.0 - p_t) ** self.gamma
        alpha_factor = targets * self.alpha + (1.0 - targets) * (1.0 - self.alpha)
        focal_loss = (alpha_factor * focal_factor * bce).mean()
        
        probs_flat = probs.view(-1)
        targets_flat = targets.view(-1)
        intersection = (probs_flat * targets_flat).sum()
        dice = (2.0 * intersection + self.smooth) / (
            probs_flat.sum() + targets_flat.sum() + self.smooth
        )
        dice_loss = 1.0 - dice
        
        return (1.0 - self.dice_weight) * focal_loss + self.dice_weight * dice_loss
