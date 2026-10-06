import pytest
from ml_models.config import risk_level
from ml_models.data.features import InputError
from ml_models.data.synthetic import (
    market_records,
    supply_chain_frame,
    transaction_records,
)
from ml_models.serving.service import ModelNotReady, ModelService


class TestService:
    def test_not_ready_without_models(self, tmp_path):
        service = ModelService(tmp_path)
        assert not service.ready()
        with pytest.raises(ModelNotReady):
            service.assess_risk(market_records(120, 1))

    def test_ready_after_bootstrap(self, trained_service):
        assert trained_service.ready()
        assert trained_service.missing() == []

    def test_liquidity_forecast_structure(self, trained_service):
        out = trained_service.forecast_liquidity(market_records(300, 5), 4, "req")
        res = out["result"]
        assert out["model_version"].startswith("liquidity_v")
        assert len(res["predicted_liquidity"]) == 4
        for lo, mid, hi in zip(
            res["lower_bound"], res["predicted_liquidity"], res["upper_bound"]
        ):
            assert lo < mid < hi
        assert all(v > 0 for v in res["predicted_liquidity"])

    def test_liquidity_horizon_and_history_validation(self, trained_service):
        with pytest.raises(InputError):
            trained_service.forecast_liquidity(market_records(300, 5), 99)
        with pytest.raises(InputError):
            trained_service.forecast_liquidity(market_records(60, 5), 2)

    def test_supply_chain_forecast(self, trained_service):
        recs = supply_chain_frame(60, 4).to_dict("records")
        res = trained_service.forecast_supply_chain(recs, 5)["result"]
        assert len(res["predictions"]) == 5
        with pytest.raises(InputError):
            trained_service.forecast_supply_chain(recs[:10], 5)
        with pytest.raises(InputError):
            trained_service.forecast_supply_chain([{"demand": 1}] * 40, 3)

    def test_risk_assessment(self, trained_service):
        res = trained_service.assess_risk(market_records(150, 6))["result"]
        assert 0 <= res["overall_risk"] <= 1
        assert res["risk_level"] == risk_level(res["overall_risk"])
        assert set(res["factors"]) == {
            "market_risk",
            "credit_risk",
            "liquidity_risk",
            "operational_risk",
            "compliance_risk",
        }

    def test_risk_orders_unverified_above_verified(self, trained_service):
        low = market_records(150, 7, verified=1.0, collateral_mean=2.2, vol_scale=0.5)
        high = market_records(150, 7, verified=0.0, collateral_mean=1.0, vol_scale=2.0)
        a = trained_service.assess_risk(low)["result"]["rule_based_overall"]
        b = trained_service.assess_risk(high)["result"]["rule_based_overall"]
        assert b > a

    def test_screening_flags_extreme_transaction(self, trained_service):
        normal, _ = transaction_records(5, 11, anomaly_fraction=0.0)
        extreme = [
            {
                "amount": 95000,
                "avg_amount_30d": 150,
                "tx_count_24h": 25,
                "account_age_days": 1,
                "kyc_score": 0.1,
                "country_risk": 0.95,
                "cross_border": 1,
                "timestamp": "2024-03-03T03:00:00Z",
            }
        ]
        res = trained_service.screen_transactions(normal + extreme)["result"]
        assert len(res) == 6
        assert res[-1]["requires_review"] is True
        assert len(res[-1]["flags"]) >= 1

    def test_second_training_creates_new_active_version(self, tmp_path):
        service = ModelService(tmp_path)
        service.train(["compliance"], "quick")
        service.train(["compliance"], "quick")
        assert service.manager.get_active_version("compliance") == "2"

    def test_unknown_profile_and_type(self, tmp_path):
        service = ModelService(tmp_path)
        with pytest.raises(ValueError):
            service.train(["risk"], "nope")
        with pytest.raises(ValueError):
            service.train(["nope"], "quick")

    def test_models_persist_across_instances(self, trained_service):
        again = ModelService(trained_service.model_dir)
        assert again.ready()
        assert again.assess_risk(market_records(150, 8))["result"]["risk_level"]
