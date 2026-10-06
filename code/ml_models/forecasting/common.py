from typing import Dict, List

import numpy as np


def split_three(n: int, val_frac: float = 0.15, test_frac: float = 0.10):
    n_test = max(1, int(n * test_frac))
    n_val = max(1, int((n - n_test) * val_frac))
    n_train = n - n_val - n_test
    if n_train < 1:
        raise ValueError("Not enough sequences for a train/validation/test split")
    return n_train, n_val, n_test


def residual_bands(preds: np.ndarray, actual: np.ndarray) -> Dict[str, List[float]]:
    resid = actual - preds
    return {
        "lower": np.quantile(resid, 0.05, axis=0).tolist(),
        "upper": np.quantile(resid, 0.95, axis=0).tolist(),
    }
