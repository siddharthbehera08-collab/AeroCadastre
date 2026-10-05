"""AeroCadastre Building Detection Neural Architectures & Loss Functions.

Implements:
- UNetBaseline: Clean, compact standard U-Net architecture for aerial building segmentation.
- ResUNet: Residual U-Net with skip connections and residual blocks for enhanced feature extraction.
- BCEDiceLoss: Configurable hybrid Binary Cross-Entropy + Soft Dice loss.
- BoundaryWeightedLoss: BCE + Dice with boundary contour emphasis.
"""

from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class DoubleConv(nn.Module):
    """(Conv2D -> BatchNorm -> ReLU) * 2"""

    def __init__(self, in_channels: int, out_channels: int, mid_channels: Optional[int] = None):
        super().__init__()
        if not mid_channels:
            mid_channels = out_channels
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(mid_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(mid_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.double_conv(x)


class Down(nn.Module):
    """Downscaling with MaxPool then DoubleConv."""

    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.maxpool_conv = nn.Sequential(
            nn.MaxPool2d(2),
            DoubleConv(in_channels, out_channels),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.maxpool_conv(x)


class Up(nn.Module):
    """Upscaling then DoubleConv with skip connection concatenation."""

    def __init__(self, in_channels: int, out_channels: int, bilinear: bool = False):
        super().__init__()
        if bilinear:
            self.up = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=True)
            self.conv = DoubleConv(in_channels, out_channels, in_channels // 2)
        else:
            self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
            self.conv = DoubleConv(in_channels, out_channels)

    def forward(self, x1: torch.Tensor, x2: torch.Tensor) -> torch.Tensor:
        x1 = self.up(x1)
        # Pad x1 if necessary to match x2 dimensions
        diff_y = x2.size()[2] - x1.size()[2]
        diff_x = x2.size()[3] - x1.size()[3]
        if diff_y != 0 or diff_x != 0:
            x1 = F.pad(x1, [diff_x // 2, diff_x - diff_x // 2, diff_y // 2, diff_y - diff_y // 2])
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)


class UNetBaseline(nn.Module):
    """Standard Compact U-Net Baseline for aerial building footprint segmentation.

    Args:
        in_channels: Number of input image channels (default 3 for RGB).
        out_channels: Number of output channels (default 1 for binary building mask).
        base_features: Number of feature maps in the first layer (default 32 for compactness & efficiency).
        bilinear: If True, uses bilinear interpolation instead of transposed conv for upsampling.
    """

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 1,
        base_features: int = 32,
        bilinear: bool = False,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.bilinear = bilinear

        self.inc = DoubleConv(in_channels, base_features)
        self.down1 = Down(base_features, base_features * 2)
        self.down2 = Down(base_features * 2, base_features * 4)
        self.down3 = Down(base_features * 4, base_features * 8)
        factor = 2 if bilinear else 1
        self.down4 = Down(base_features * 8, (base_features * 16) // factor)

        self.up1 = Up(base_features * 16, (base_features * 8) // factor, bilinear)
        self.up2 = Up(base_features * 8, (base_features * 4) // factor, bilinear)
        self.up3 = Up(base_features * 4, (base_features * 2) // factor, bilinear)
        self.up4 = Up(base_features * 2, base_features, bilinear)
        self.outc = nn.Conv2d(base_features, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)

        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        logits = self.outc(x)
        return logits


class ResidualBlock(nn.Module):
    """Residual convolutional block with identity shortcut or 1x1 projection."""

    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)

        if in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
                nn.BatchNorm2d(out_channels),
            )
        else:
            self.shortcut = nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = self.shortcut(x)
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = self.relu(out + identity)
        return out


class ResUNet(nn.Module):
    """Residual U-Net (ResUNet) for precise building boundary and footprint segmentation.

    Leverages residual blocks in encoder and decoder to maintain gradient flow
    and capture high-frequency corner and boundary details in aerial imagery.
    """

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 1,
        base_features: int = 32,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels

        # Encoder
        self.enc1 = ResidualBlock(in_channels, base_features)
        self.pool1 = nn.MaxPool2d(2)
        self.enc2 = ResidualBlock(base_features, base_features * 2)
        self.pool2 = nn.MaxPool2d(2)
        self.enc3 = ResidualBlock(base_features * 2, base_features * 4)
        self.pool3 = nn.MaxPool2d(2)
        self.enc4 = ResidualBlock(base_features * 4, base_features * 8)
        self.pool4 = nn.MaxPool2d(2)

        # Bridge
        self.bridge = ResidualBlock(base_features * 8, base_features * 16)

        # Decoder
        self.up4 = nn.ConvTranspose2d(base_features * 16, base_features * 8, kernel_size=2, stride=2)
        self.dec4 = ResidualBlock(base_features * 16, base_features * 8)

        self.up3 = nn.ConvTranspose2d(base_features * 8, base_features * 4, kernel_size=2, stride=2)
        self.dec3 = ResidualBlock(base_features * 8, base_features * 4)

        self.up2 = nn.ConvTranspose2d(base_features * 4, base_features * 2, kernel_size=2, stride=2)
        self.dec2 = ResidualBlock(base_features * 4, base_features * 2)

        self.up1 = nn.ConvTranspose2d(base_features * 2, base_features, kernel_size=2, stride=2)
        self.dec1 = ResidualBlock(base_features * 2, base_features)

        self.outc = nn.Conv2d(base_features, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool1(e1))
        e3 = self.enc3(self.pool2(e2))
        e4 = self.enc4(self.pool3(e3))

        b = self.bridge(self.pool4(e4))

        d4 = self.up4(b)
        d4 = self.dec4(torch.cat([d4, e4], dim=1))

        d3 = self.up3(d4)
        d3 = self.dec3(torch.cat([d3, e3], dim=1))

        d2 = self.up2(d3)
        d2 = self.dec2(torch.cat([d2, e2], dim=1))

        d1 = self.up1(d2)
        d1 = self.dec1(torch.cat([d1, e1], dim=1))

        return self.outc(d1)


class BCEDiceLoss(nn.Module):
    """Combined Binary Cross-Entropy + Soft Dice Loss for building footprint segmentation.

    Args:
        bce_weight: Weight assigned to BCE loss (1 - bce_weight assigned to Dice).
        smooth: Smoothing coefficient to prevent division by zero in Dice score.
        pos_weight: Optional positive class weighting for BCE to balance sparse buildings.
    """

    def __init__(self, bce_weight: float = 0.5, smooth: float = 1.0, pos_weight: Optional[float] = None):
        super().__init__()
        self.bce_weight = bce_weight
        self.smooth = smooth
        if pos_weight is not None:
            self.bce = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pos_weight]))
        else:
            self.bce = nn.BCEWithLogitsLoss()

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        if self.bce.pos_weight is not None and self.bce.pos_weight.device != logits.device:
            self.bce.pos_weight = self.bce.pos_weight.to(logits.device)

        bce_loss = self.bce(logits, targets)

        probs = torch.sigmoid(logits)
        probs_flat = probs.view(-1)
        targets_flat = targets.view(-1)

        intersection = (probs_flat * targets_flat).sum()
        union = probs_flat.sum() + targets_flat.sum()
        dice_score = (2.0 * intersection + self.smooth) / (union + self.smooth)
        dice_loss = 1.0 - dice_score

        return self.bce_weight * bce_loss + (1.0 - self.bce_weight) * dice_loss


class FocalLoss(nn.Module):
    """Focal Loss to focus learning on hard examples (e.g. dense building boundaries)."""

    def __init__(self, alpha: float = 0.25, gamma: float = 2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce = F.binary_cross_entropy_with_logits(logits, targets, reduction="none")
        probs = torch.sigmoid(logits)
        p_t = probs * targets + (1 - probs) * (1 - targets)
        alpha_factor = self.alpha * targets + (1 - self.alpha) * (1 - targets)
        modulating_factor = (1.0 - p_t) ** self.gamma
        loss = alpha_factor * modulating_factor * bce
        return loss.mean()


class FocalDiceLoss(nn.Module):
    """Combined Focal Loss + Soft Dice Loss for robust building footprint segmentation."""

    def __init__(self, focal_weight: float = 0.5, alpha: float = 0.25, gamma: float = 2.0, smooth: float = 1.0):
        super().__init__()
        self.focal_weight = focal_weight
        self.focal = FocalLoss(alpha=alpha, gamma=gamma)
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        focal_loss = self.focal(logits, targets)

        probs = torch.sigmoid(logits)
        probs_flat = probs.view(-1)
        targets_flat = targets.view(-1)

        intersection = (probs_flat * targets_flat).sum()
        union = probs_flat.sum() + targets_flat.sum()
        dice_loss = 1.0 - (2.0 * intersection + self.smooth) / (union + self.smooth)

        return self.focal_weight * focal_loss + (1.0 - self.focal_weight) * dice_loss
