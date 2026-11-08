"""Reproducible EuroSAT training harness for the labelled vision prototype.

EuroSAT provides image-level land-cover labels, not Nepal forest masks or
before/after change labels. Therefore:

* Vision Transformer training is supervised on the real EuroSAT labels.
* U-Net training uses transparent green-canopy pseudo-masks.
* Siamese training uses transparent synthetic rectangle-change pairs.

The latter two metrics measure proxy-task performance only and must not be
presented as Nepal or real-world change-detection accuracy.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Iterable

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, Subset
from torchvision import datasets, transforms

CLASSES = (
    "AnnualCrop", "Forest", "HerbaceousVegetation", "Highway", "Industrial",
    "Pasture", "PermanentCrop", "Residential", "River", "SeaLake",
)


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def device_for_training() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class TinyVisionTransformer(nn.Module):
    def __init__(self, classes: int = 10, dim: int = 96) -> None:
        super().__init__()
        self.patch = nn.Conv2d(3, dim, kernel_size=8, stride=8)
        self.cls = nn.Parameter(torch.zeros(1, 1, dim))
        self.pos = nn.Parameter(torch.zeros(1, 65, dim))
        layer = nn.TransformerEncoderLayer(dim, 4, dim * 4, batch_first=True, dropout=0.1)
        self.encoder = nn.TransformerEncoder(layer, 3)
        self.head = nn.Linear(dim, classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.patch(x).flatten(2).transpose(1, 2)
        cls = self.cls.expand(x.shape[0], -1, -1)
        x = self.encoder(torch.cat([cls, x], dim=1) + self.pos)
        return self.head(x[:, 0])


class DoubleConv(nn.Module):
    def __init__(self, inputs: int, outputs: int) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(inputs, outputs, 3, padding=1), nn.BatchNorm2d(outputs), nn.ReLU(),
            nn.Conv2d(outputs, outputs, 3, padding=1), nn.BatchNorm2d(outputs), nn.ReLU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class TinyUNet(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.down1 = DoubleConv(3, 32)
        self.down2 = DoubleConv(32, 64)
        self.pool = nn.MaxPool2d(2)
        self.up = nn.ConvTranspose2d(64, 32, 2, stride=2)
        self.out = nn.Conv2d(64, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        a = self.down1(x)
        b = self.down2(self.pool(a))
        return self.out(torch.cat([self.up(b), a], dim=1))


class TinySiamese(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 24, 3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2), nn.Conv2d(24, 48, 3, padding=1), nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(48, 24, 2, stride=2), nn.ReLU(),
            nn.Conv2d(24, 1, 1),
        )

    def forward(self, baseline: torch.Tensor, comparison: torch.Tensor) -> torch.Tensor:
        return self.decoder(torch.abs(self.encoder(baseline) - self.encoder(comparison)))


class PseudoMaskDataset(Dataset):
    def __init__(self, base: Dataset) -> None:
        self.base = base

    def __len__(self) -> int:
        return len(self.base)

    def __getitem__(self, index: int):
        image, _ = self.base[index]
        # A reproducible proxy label: green-dominant canopy pixels.
        mask = ((image[1] > image[0] * 0.95) & (image[1] > image[2] * 0.9)).float()
        return image, mask.unsqueeze(0)


class SyntheticChangeDataset(Dataset):
    def __init__(self, base: Dataset, seed: int = 42) -> None:
        self.base = base
        self.seed = seed

    def __len__(self) -> int:
        return len(self.base)

    def __getitem__(self, index: int):
        image, _ = self.base[index]
        rng = random.Random(self.seed + index)
        size = rng.randint(8, 20)
        top = rng.randint(0, 64 - size)
        left = rng.randint(0, 64 - size)
        changed = image.clone()
        changed[:, top:top + size, left:left + size] *= 0.12
        target = torch.zeros((1, 64, 64))
        target[:, top:top + size, left:left + size] = 1
        return image, changed, target


def loaders(root: Path, limit: int, seed: int) -> tuple[DataLoader, DataLoader, Dataset]:
    tfm = transforms.Compose([
        transforms.ToTensor(),
        transforms.Resize((64, 64), antialias=True),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
    ])
    data = datasets.EuroSAT(root=str(root), download=True, transform=tfm)
    indices = list(range(min(limit, len(data))))
    rng = random.Random(seed)
    rng.shuffle(indices)
    split = max(1, int(len(indices) * 0.8))
    train = Subset(data, indices[:split])
    valid = Subset(data, indices[split:])
    return DataLoader(train, 32, shuffle=True), DataLoader(valid, 32), data


def classification_metrics(model: nn.Module, loader: DataLoader, device: torch.device) -> dict[str, float]:
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for images, labels in loader:
            output = model(images.to(device))
            correct += (output.argmax(1).cpu() == labels).sum().item()
            total += labels.numel()
    return {"accuracy": round(correct / max(total, 1), 4)}


def segmentation_iou(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    intersection = union = 0
    with torch.no_grad():
        for images, masks in loader:
            pred = torch.sigmoid(model(images.to(device))).cpu() > 0.5
            truth = masks > 0.5
            intersection += (pred & truth).sum().item()
            union += (pred | truth).sum().item()
    return round(intersection / max(union, 1), 4)


def change_iou(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    intersection = union = 0
    with torch.no_grad():
        for before, after, masks in loader:
            pred = torch.sigmoid(model(before.to(device), after.to(device))).cpu() > 0.5
            truth = masks > 0.5
            intersection += (pred & truth).sum().item()
            union += (pred | truth).sum().item()
    return round(intersection / max(union, 1), 4)


def train_epoch(model: nn.Module, loader: Iterable, loss_fn: nn.Module, optimizer, device: torch.device) -> float:
    model.train()
    total = 0.0
    batches = 0
    for batch in loader:
        optimizer.zero_grad(set_to_none=True)
        if len(batch) == 2:
            images, target = batch
            output = model(images.to(device))
            target = target.to(device)
        else:
            before, after, target = batch
            output = model(before.to(device), after.to(device))
            target = target.to(device)
        loss = loss_fn(output, target)
        loss.backward()
        optimizer.step()
        total += float(loss.item())
        batches += 1
    return round(total / max(batches, 1), 5)


def run(args: argparse.Namespace) -> dict:
    seed_everything(args.seed)
    device = device_for_training()
    train_loader, valid_loader, base = loaders(Path(args.data_dir), args.limit, args.seed)
    train_images = PseudoMaskDataset(Subset(base, train_loader.dataset.indices))
    valid_images = PseudoMaskDataset(Subset(base, valid_loader.dataset.indices))
    train_masks = DataLoader(train_images, 32, shuffle=True)
    valid_masks = DataLoader(valid_images, 32)
    train_changes = DataLoader(SyntheticChangeDataset(Subset(base, train_loader.dataset.indices), args.seed), 32, shuffle=True)
    valid_changes = DataLoader(SyntheticChangeDataset(Subset(base, valid_loader.dataset.indices), args.seed), 32)
    results: dict = {"dataset": "EuroSAT RGB", "classes": CLASSES, "device": str(device), "limit": args.limit, "epochs": args.epochs, "tasks": {}}

    vit = TinyVisionTransformer().to(device)
    optimizer = torch.optim.AdamW(vit.parameters(), lr=3e-4, weight_decay=1e-4)
    for _ in range(args.epochs):
        train_epoch(vit, train_loader, nn.CrossEntropyLoss(), optimizer, device)
    results["tasks"]["vision_transformer"] = {
        "label_source": "real EuroSAT image-level land-cover labels",
        "validation": classification_metrics(vit, valid_loader, device),
        "model": "TinyVisionTransformer",
    }

    unet = TinyUNet().to(device)
    optimizer = torch.optim.AdamW(unet.parameters(), lr=1e-3)
    for _ in range(args.epochs):
        train_epoch(unet, train_masks, nn.BCEWithLogitsLoss(), optimizer, device)
    results["tasks"]["unet"] = {
        "label_source": "green-dominance pseudo-mask derived from EuroSAT RGB",
        "validation_iou": segmentation_iou(unet, valid_masks, device),
        "model": "TinyUNet",
    }

    siamese = TinySiamese().to(device)
    optimizer = torch.optim.AdamW(siamese.parameters(), lr=1e-3)
    for _ in range(args.epochs):
        train_epoch(siamese, train_changes, nn.BCEWithLogitsLoss(), optimizer, device)
    results["tasks"]["siamese"] = {
        "label_source": "synthetic darkened-rectangle change masks derived from EuroSAT RGB",
        "validation_iou": change_iou(siamese, valid_changes, device),
        "model": "TinySiamese",
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2) + "\n")
    torch.save({"model": vit.state_dict(), "classes": CLASSES}, output.with_name("vision_transformer.pt"))
    torch.save({"model": unet.state_dict(), "label_source": results["tasks"]["unet"]["label_source"]}, output.with_name("unet.pt"))
    torch.save({"model": siamese.state_dict(), "label_source": results["tasks"]["siamese"]["label_source"]}, output.with_name("siamese.pt"))
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="backend/mrv/artifacts/eurosat")
    parser.add_argument("--output", default="backend/mrv/artifacts/training_metrics.json")
    parser.add_argument("--limit", type=int, default=3000)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2))


if __name__ == "__main__":
    main()
