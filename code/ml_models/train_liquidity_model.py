import logging
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from torch.utils.data import DataLoader, Dataset

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class LiquidityLSTM(nn.Module):
    """
    LSTM-based model with attention mechanism for predicting synthetic asset liquidity.
    Input features (10): Price, Volume, Volatility, Interest Rate, Time-to-Maturity,
                         Collateral Ratio, Gas Price, Network Congestion, TVL, Pool Size.
    Output (1): Predicted next-period liquidity depth.
    """

    def __init__(
        self,
        input_size: Any = 10,
        hidden_size: Any = 64,
        num_layers: Any = 3,
        num_heads: Any = 4,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            bidirectional=True,
            batch_first=True,
        )
        self.attention = nn.MultiheadAttention(
            embed_dim=2 * hidden_size, num_heads=num_heads, batch_first=True
        )
        self.fc = nn.Sequential(
            nn.Linear(2 * hidden_size, hidden_size),
            nn.GELU(),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, x: Any) -> Any:
        lstm_out, _ = self.lstm(x)
        attn_output, _ = self.attention(lstm_out, lstm_out, lstm_out)
        return self.fc(attn_output[:, -1])


class TimeSeriesDataset(Dataset):
    """Custom Dataset for time series data."""

    def __init__(self, X: Any, y: Any) -> None:
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32).unsqueeze(1)

    def __len__(self) -> Any:
        return len(self.X)

    def __getitem__(self, idx: Any) -> Any:
        return (self.X[idx], self.y[idx])


def create_sequences(data: Any, seq_length: Any) -> Any:
    """Convert time series data into sequences for LSTM."""
    X, y = ([], [])
    for i in range(len(data) - seq_length):
        X.append(data[i : i + seq_length])
        y.append(data[i + seq_length, -1])
    return (np.array(X), np.array(y))


def simulate_data(
    n_samples: Any = 5000, n_features: Any = 10, seq_length: Any = 20
) -> Any:
    """Simulate time series data for liquidity prediction."""
    logger.info(f"Simulating {n_samples} time steps of data...")
    np.random.seed(42)
    data = np.zeros((n_samples, n_features))
    for i in range(n_features - 1):
        data[:, i] = np.cumsum(np.random.randn(n_samples) * 0.1) + np.random.rand() * 10
    data[:, -1] = (
        data[:, 0] * 0.5
        + data[:, 1] * 0.3
        - data[:, 2] * 0.2
        + data[:, 8] * 0.1
        + np.sin(np.arange(n_samples) / 100) * 2
        + np.random.randn(n_samples) * 0.5
    )
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data)
    X, y = create_sequences(scaled_data, seq_length)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )
    logger.info(f"Training set size: {len(X_train)} sequences")
    logger.info(f"Testing set size: {len(X_test)} sequences")
    return (
        TimeSeriesDataset(X_train, y_train),
        TimeSeriesDataset(X_test, y_test),
        scaler,
    )


def train_model(epochs: Any = 10, batch_size: Any = 64, seq_length: Any = 20) -> Any:
    """
    Full training pipeline for the Liquidity Prediction Model.
    """
    logger.info("Starting Liquidity Prediction Model training...")
    train_dataset, test_dataset, scaler = simulate_data(seq_length=seq_length)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    model = LiquidityLSTM(input_size=train_dataset.X.shape[-1])
    criterion = nn.MSELoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.0003)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    logger.info(f"Using device: {device}")
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = (batch_X.to(device), batch_y.to(device))
            optimizer.zero_grad()
            output = model(batch_X)
            loss = criterion(output, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        avg_train_loss = total_loss / len(train_loader)
        model.eval()
        test_loss = 0
        with torch.no_grad():
            for batch_X, batch_y in test_loader:
                batch_X, batch_y = (batch_X.to(device), batch_y.to(device))
                output = model(batch_X)
                loss = criterion(output, batch_y)
                test_loss += loss.item()
        avg_test_loss = test_loss / len(test_loader)
        logger.info(
            f"Epoch {epoch + 1}/{epochs} | Train Loss: {avg_train_loss:.6f} | Test Loss: {avg_test_loss:.6f}"
        )
    model_path = "liquidity_predictor.pt"
    torch.save(model.state_dict(), model_path)
    logger.info(f"Model trained and saved to {model_path}")
    return (model, scaler)


if __name__ == "__main__":
    trained_model, data_scaler = train_model(epochs=5)
    dummy_input = np.random.rand(1, 20, 10)
    scaled_dummy_input = data_scaler.transform(dummy_input[0, -1, :].reshape(1, -1))
    dummy_sequence = torch.tensor(dummy_input, dtype=torch.float32)
    trained_model.eval()
    with torch.no_grad():
        prediction = trained_model(dummy_sequence)
    dummy_inverse = np.zeros((1, 10))
    dummy_inverse[:, -1] = prediction.cpu().numpy().flatten()
    original_scale_prediction = data_scaler.inverse_transform(dummy_inverse)[:, -1]
    logger.info(f"Dummy Prediction (Scaled): {prediction.item():.4f}")
    logger.info(
        f"Dummy Prediction (Original Scale - Liquidity): {original_scale_prediction[0]:.2f}"
    )
