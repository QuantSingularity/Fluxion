from ml_models.networks.architectures import (
    AnomalyAutoencoder,
    ComplianceViolationDetector,
    FinancialRiskLSTM,
    LiquidityLSTM,
    SupplyChainForecaster,
)


class TestModels:
    def test_forward_shapes(self):
        import torch

        assert LiquidityLSTM(10, 8, 1, 0.0)(torch.zeros(3, 24, 10)).shape == (3, 6)
        assert SupplyChainForecaster(12, 8, 1, 0.0)(torch.zeros(3, 30, 12)).shape == (
            3,
            5,
        )
        out = FinancialRiskLSTM(12, 8, 1, 0.0)(torch.zeros(3, 30, 12))
        assert out["overall_risk"].shape == (3, 1)
        assert out["market_risk"].shape == (3, 1)
        recon, enc = AnomalyAutoencoder(12, 3, 0.0)(torch.zeros(1, 12))
        assert recon.shape == (1, 12) and enc.shape == (1, 3)
        assert len(ComplianceViolationDetector(12, 8, 0.0)(torch.zeros(1, 12))) == 6

    def test_single_sample_inference_with_eval(self):
        import torch

        model = AnomalyAutoencoder(12, 3, 0.2).eval()
        recon, _ = model(torch.zeros(1, 12))
        assert torch.isfinite(recon).all()
