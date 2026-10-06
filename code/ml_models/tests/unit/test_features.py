import numpy as np
import pytest
from ml_models.data.features import (
    InputError,
    build_risk_features,
    risk_targets,
    transaction_features,
    transaction_frame,
)
from ml_models.data.synthetic import market_records, transaction_records


class TestFeatures:
    def test_risk_features_shape_and_bounds(self):
        feats = build_risk_features(market_records(200, 1))
        assert feats.shape[1] == 12
        assert not feats.isna().any().any()
        assert feats["utilization"].between(0, 1).all()

    def test_risk_targets_bounded(self):
        feats = build_risk_features(market_records(200, 2))
        targets = risk_targets(feats)
        assert targets.shape[1] == 5
        assert targets.min().min() >= 0 and targets.max().max() <= 1

    def test_risk_features_reject_short_history(self):
        with pytest.raises(InputError):
            build_risk_features(market_records(20, 1))

    def test_risk_features_reject_missing_fields(self):
        with pytest.raises(InputError):
            build_risk_features([{"price": 1.0}] * 80)

    def test_transaction_validation(self):
        with pytest.raises(InputError):
            transaction_frame([{"amount": -5}])
        with pytest.raises(InputError):
            transaction_frame([{"nope": 1}])
        with pytest.raises(InputError):
            transaction_frame([{"amount": "abc"}])
        with pytest.raises(InputError):
            transaction_frame([])

    def test_transaction_features_finite(self):
        records, _ = transaction_records(100, 3)
        X = transaction_features(transaction_frame(records))
        assert X.shape == (100, 12)
        assert np.isfinite(X).all()
