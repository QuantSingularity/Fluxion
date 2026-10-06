import pytest
from ml_models.core.registry import ModelVersionManager


class TestRegistry:
    def test_register_activate_and_ab(self, tmp_path):
        mgr = ModelVersionManager(tmp_path)
        mgr.register_model("liquidity", tmp_path / "liquidity" / "v1", "1")
        mgr.register_model("liquidity", tmp_path / "liquidity" / "v2", "2")
        mgr.activate_model("liquidity", "2")
        assert mgr.get_active_version("liquidity") == "2"
        assert mgr.next_version("liquidity") == "3"
        mgr.configure_ab_test("liquidity", ["1", "2"], [50, 50])
        picks = {mgr.select_model_for_request("liquidity", f"r{i}") for i in range(50)}
        assert picks == {"1", "2"}
        assert mgr.select_model_for_request(
            "liquidity", "same"
        ) == mgr.select_model_for_request("liquidity", "same")
        reloaded = ModelVersionManager(tmp_path)
        assert reloaded.get_active_version("liquidity") == "2"

    def test_rejects_bad_split_and_unknown_version(self, tmp_path):
        mgr = ModelVersionManager(tmp_path)
        mgr.register_model("risk", tmp_path / "r", "1")
        with pytest.raises(ValueError):
            mgr.configure_ab_test("risk", ["1"], [90])
        with pytest.raises(ValueError):
            mgr.activate_model("risk", "9")

    def test_inference_metrics(self, tmp_path):
        mgr = ModelVersionManager(tmp_path)
        mgr.record_inference("m_v1", 0.2)
        mgr.record_inference("m_v1", 0.4, error=True)
        m = mgr.get_model_metrics("m_v1")
        assert m["inference_count"] == 2 and m["error_count"] == 1
        assert m["avg_inference_time"] == pytest.approx(0.3)
