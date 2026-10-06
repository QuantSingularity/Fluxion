import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ServiceSettings:
    model_path: Path
    port: int
    metrics_port: int
    log_level: str
    api_key: str
    auto_bootstrap: bool
    bootstrap_profile: str

    @classmethod
    def from_env(cls) -> "ServiceSettings":
        return cls(
            model_path=Path(os.environ.get("MODEL_PATH", "/app/models")),
            port=int(os.environ.get("PORT", "8000")),
            metrics_port=int(os.environ.get("METRICS_PORT", "9091")),
            log_level=os.environ.get("LOG_LEVEL", "info").lower(),
            api_key=os.environ.get("ML_SERVICE_API_KEY", ""),
            auto_bootstrap=_env_bool("ML_AUTO_BOOTSTRAP", True),
            bootstrap_profile=os.environ.get("ML_BOOTSTRAP_PROFILE", "full"),
        )
