from typing import Any

import pandas as pd
from sklearn.preprocessing import RobustScaler


class DataPipeline:

    def __init__(self) -> None:
        self.scaler = RobustScaler()
        self.features = [
            "volume",
            "price",
            "liquidity",
            "volatility",
            "arbitrage_opportunities",
        ]

    def transform(self, raw_data: Any) -> Any:
        df = pd.DataFrame(raw_data)
        df["price_velocity"] = df["price"].pct_change()
        df["liquidity_zscore"] = (df["liquidity"] - df["liquidity"].mean()) / df[
            "liquidity"
        ].std()
        df = df[(df["volume"] > 0) & (df["price"] > 0)]
        scaled = self.scaler.fit_transform(df[self.features])
        return pd.DataFrame(scaled, columns=self.features)
