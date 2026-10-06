from __future__ import annotations

import copy
import logging
import random
from typing import Any, Callable, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)

StepFn = Callable[[nn.Module, torch.Tensor, torch.Tensor], torch.Tensor]


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def make_loader(
    X: Any, y: Any, batch_size: int = 64, shuffle: bool = False
) -> DataLoader:
    features = torch.as_tensor(np.asarray(X), dtype=torch.float32)
    targets = torch.as_tensor(np.asarray(y), dtype=torch.float32)
    if targets.ndim == 1:
        targets = targets.unsqueeze(1)
    return DataLoader(
        TensorDataset(features, targets), batch_size=batch_size, shuffle=shuffle
    )


class ModelTrainer:
    def __init__(
        self,
        model: nn.Module,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-5,
        step_fn: Optional[StepFn] = None,
        grad_clip: float = 1.0,
        device: Optional[torch.device] = None,
    ) -> None:
        self.model = model
        self.device = device or get_device()
        self.model.to(self.device)
        self.optimizer = torch.optim.AdamW(
            model.parameters(), lr=learning_rate, weight_decay=weight_decay
        )
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode="min", patience=3, factor=0.5
        )
        self.criterion = nn.MSELoss()
        self.step_fn = step_fn or self._default_step
        self.grad_clip = grad_clip

    def _default_step(
        self, model: nn.Module, xb: torch.Tensor, yb: torch.Tensor
    ) -> torch.Tensor:
        return self.criterion(model(xb), yb)

    def _run_epoch(self, loader: DataLoader, train: bool) -> float:
        self.model.train(train)
        total = 0.0
        count = 0
        context = torch.enable_grad() if train else torch.no_grad()
        with context:
            for xb, yb in loader:
                xb = xb.to(self.device)
                yb = yb.to(self.device)
                if train:
                    self.optimizer.zero_grad()
                loss = self.step_fn(self.model, xb, yb)
                if train:
                    loss.backward()
                    if self.grad_clip:
                        torch.nn.utils.clip_grad_norm_(
                            self.model.parameters(), self.grad_clip
                        )
                    self.optimizer.step()
                total += float(loss.item()) * len(xb)
                count += len(xb)
        return total / max(count, 1)

    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        epochs: int = 100,
        patience: int = 10,
    ) -> Tuple[List[float], List[float]]:
        if len(train_loader) == 0 or len(val_loader) == 0:
            raise ValueError("train and validation loaders must not be empty")

        best_loss = float("inf")
        best_state = copy.deepcopy(self.model.state_dict())
        stale = 0
        train_losses: List[float] = []
        val_losses: List[float] = []

        for epoch in range(epochs):
            train_loss = self._run_epoch(train_loader, train=True)
            val_loss = self._run_epoch(val_loader, train=False)
            train_losses.append(train_loss)
            val_losses.append(val_loss)
            self.scheduler.step(val_loss)
            logger.info(
                "Epoch %d/%d train=%.6f val=%.6f",
                epoch + 1,
                epochs,
                train_loss,
                val_loss,
            )
            if val_loss < best_loss - 1e-9:
                best_loss = val_loss
                best_state = copy.deepcopy(self.model.state_dict())
                stale = 0
            else:
                stale += 1
                if stale >= patience:
                    logger.info("Early stopping at epoch %d", epoch + 1)
                    break

        self.model.load_state_dict(best_state)
        self.model.eval()
        return train_losses, val_losses

    def evaluate(self, loader: DataLoader) -> Tuple[float, np.ndarray, np.ndarray]:
        if len(loader) == 0:
            raise ValueError("loader must not be empty")
        self.model.eval()
        preds: List[np.ndarray] = []
        actuals: List[np.ndarray] = []
        total = 0.0
        count = 0
        with torch.no_grad():
            for xb, yb in loader:
                xb = xb.to(self.device)
                yb = yb.to(self.device)
                out = self.model(xb)
                total += float(self.criterion(out, yb).item()) * len(xb)
                count += len(xb)
                preds.append(out.cpu().numpy())
                actuals.append(yb.cpu().numpy())
        return total / max(count, 1), np.concatenate(preds), np.concatenate(actuals)
