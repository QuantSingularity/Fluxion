from __future__ import annotations

from typing import Dict

import torch
import torch.nn as nn
from ml_models.config import (
    LIQUIDITY_HORIZON,
    RISK_FACTORS,
    SUPPLY_CHAIN_HORIZON,
    VIOLATION_TYPES,
)


def choose_num_heads(embed_dim: int, preferred: int = 8) -> int:
    heads = min(preferred, embed_dim)
    while heads > 1:
        if embed_dim % heads == 0:
            return heads
        heads -= 1
    return 1


def _lstm_dropout(num_layers: int, dropout: float) -> float:
    return float(dropout) if num_layers > 1 else 0.0


class LiquidityLSTM(nn.Module):
    def __init__(
        self,
        input_size: int = 20,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        bidirectional: bool = True,
        horizon: int = LIQUIDITY_HORIZON,
    ) -> None:
        super().__init__()
        self.input_size = int(input_size)
        self.hidden_size = int(hidden_size)
        self.num_layers = int(num_layers)
        self.bidirectional = bool(bidirectional)
        self.horizon = int(horizon)
        self.lstm = nn.LSTM(
            input_size=self.input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            batch_first=True,
            dropout=_lstm_dropout(self.num_layers, dropout),
            bidirectional=self.bidirectional,
        )
        width = self.hidden_size * (2 if self.bidirectional else 1)
        self.attention = nn.MultiheadAttention(
            embed_dim=width, num_heads=choose_num_heads(width), batch_first=True
        )
        mid = max(width // 2, 1)
        low = max(width // 4, 1)
        self.fc1 = nn.Linear(width, mid)
        self.norm1 = nn.LayerNorm(mid)
        self.fc2 = nn.Linear(mid, low)
        self.norm2 = nn.LayerNorm(low)
        self.fc3 = nn.Linear(low, self.horizon)
        self.act = nn.GELU()
        self.drop = nn.Dropout(float(dropout))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        seq, _ = self.lstm(x)
        attended, _ = self.attention(seq, seq, seq)
        h = attended[:, -1]
        h = self.drop(self.act(self.norm1(self.fc1(h))))
        h = self.drop(self.act(self.norm2(self.fc2(h))))
        return self.fc3(h)


class SupplyChainForecaster(nn.Module):
    def __init__(
        self,
        input_size: int = 12,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        horizon: int = SUPPLY_CHAIN_HORIZON,
    ) -> None:
        super().__init__()
        self.input_size = int(input_size)
        self.hidden_size = int(hidden_size)
        self.num_layers = int(num_layers)
        self.horizon = int(horizon)
        self.conv1 = nn.Conv1d(self.input_size, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(32, 64, kernel_size=3, padding=1)
        self.lstm = nn.LSTM(
            input_size=64,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            batch_first=True,
            dropout=_lstm_dropout(self.num_layers, dropout),
        )
        self.attention = nn.MultiheadAttention(
            embed_dim=self.hidden_size,
            num_heads=choose_num_heads(self.hidden_size, 4),
            batch_first=True,
        )
        self.fc1 = nn.Linear(self.hidden_size, max(self.hidden_size // 2, 1))
        self.fc2 = nn.Linear(self.fc1.out_features, self.horizon)
        self.act = nn.ReLU()
        self.drop = nn.Dropout(float(dropout))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = x.permute(0, 2, 1)
        h = self.act(self.conv1(h))
        h = self.act(self.conv2(h))
        seq, _ = self.lstm(h.permute(0, 2, 1))
        attended, _ = self.attention(seq, seq, seq)
        h = self.drop(self.act(self.fc1(attended[:, -1])))
        return self.fc2(h)


class FinancialRiskLSTM(nn.Module):
    def __init__(
        self,
        input_size: int = 12,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.input_size = int(input_size)
        self.hidden_size = int(hidden_size)
        self.num_layers = int(num_layers)
        self.num_risk_factors = len(RISK_FACTORS)
        self.lstm = nn.LSTM(
            input_size=self.input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            batch_first=True,
            dropout=_lstm_dropout(self.num_layers, dropout),
            bidirectional=True,
        )
        width = self.hidden_size * 2
        self.attention = nn.MultiheadAttention(
            embed_dim=width,
            num_heads=choose_num_heads(width),
            dropout=float(dropout),
            batch_first=True,
        )
        mid = max(self.hidden_size // 2, 1)
        self.features = nn.Sequential(
            nn.Linear(width, self.hidden_size),
            nn.LayerNorm(self.hidden_size),
            nn.ReLU(),
            nn.Dropout(float(dropout)),
            nn.Linear(self.hidden_size, mid),
            nn.LayerNorm(mid),
            nn.ReLU(),
            nn.Dropout(float(dropout)),
        )
        self.factor_head = nn.Linear(mid, self.num_risk_factors)
        self.aggregator = nn.Sequential(
            nn.Linear(self.num_risk_factors, self.num_risk_factors * 2),
            nn.ReLU(),
            nn.Linear(self.num_risk_factors * 2, 1),
        )

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        seq, _ = self.lstm(x)
        attended, _ = self.attention(seq, seq, seq)
        h = self.features(attended[:, -1])
        factors = torch.sigmoid(self.factor_head(h))
        overall = torch.sigmoid(self.aggregator(factors))
        out = {name: factors[:, i : i + 1] for i, name in enumerate(RISK_FACTORS)}
        out["overall_risk"] = overall
        return out


class AnomalyAutoencoder(nn.Module):
    def __init__(
        self, input_size: int = 12, encoding_dim: int = 4, dropout: float = 0.1
    ) -> None:
        super().__init__()
        self.input_size = int(input_size)
        self.encoding_dim = int(encoding_dim)
        wide = max(self.input_size, 16)
        narrow = max(wide // 2, self.encoding_dim + 1)
        self.encoder = nn.Sequential(
            nn.Linear(self.input_size, wide),
            nn.LayerNorm(wide),
            nn.ReLU(),
            nn.Dropout(float(dropout)),
            nn.Linear(wide, narrow),
            nn.LayerNorm(narrow),
            nn.ReLU(),
            nn.Linear(narrow, self.encoding_dim),
            nn.Tanh(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(self.encoding_dim, narrow),
            nn.LayerNorm(narrow),
            nn.ReLU(),
            nn.Dropout(float(dropout)),
            nn.Linear(narrow, wide),
            nn.LayerNorm(wide),
            nn.ReLU(),
            nn.Linear(wide, self.input_size),
        )

    def forward(self, x: torch.Tensor):
        encoded = self.encoder(x)
        return self.decoder(encoded), encoded


class ComplianceViolationDetector(nn.Module):
    def __init__(
        self,
        input_size: int = 12,
        hidden_size: int = 64,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.input_size = int(input_size)
        self.hidden_size = int(hidden_size)
        self.num_classes = len(VIOLATION_TYPES)
        mid = max(self.hidden_size // 2, 1)
        self.network = nn.Sequential(
            nn.Linear(self.input_size, self.hidden_size * 2),
            nn.LayerNorm(self.hidden_size * 2),
            nn.ReLU(),
            nn.Dropout(float(dropout)),
            nn.Linear(self.hidden_size * 2, self.hidden_size),
            nn.LayerNorm(self.hidden_size),
            nn.ReLU(),
            nn.Dropout(float(dropout)),
            nn.Linear(self.hidden_size, mid),
            nn.LayerNorm(mid),
            nn.ReLU(),
        )
        self.head = nn.Linear(mid, self.num_classes)

    def logits(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.network(x))

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        probs = torch.sigmoid(self.logits(x))
        return {name: probs[:, i : i + 1] for i, name in enumerate(VIOLATION_TYPES)}
