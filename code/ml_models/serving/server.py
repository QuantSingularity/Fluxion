from __future__ import annotations

import logging
import signal
import threading
from http.server import ThreadingHTTPServer
from typing import Any, Tuple

from ml_models.config import ServiceSettings
from ml_models.serving.app import Application
from ml_models.serving.handlers import make_handler
from ml_models.serving.metrics import make_metrics_handler
from ml_models.serving.service import ModelService

logger = logging.getLogger("ml-service")


def create_servers(
    settings: ServiceSettings, service: ModelService, host: str = "0.0.0.0"
) -> Tuple[ThreadingHTTPServer, ThreadingHTTPServer, Application]:
    app = Application(settings, service)
    api = ThreadingHTTPServer((host, settings.port), make_handler(app))
    metrics = ThreadingHTTPServer(
        (host, settings.metrics_port), make_metrics_handler(app)
    )
    api.daemon_threads = True
    metrics.daemon_threads = True
    return api, metrics, app


def main() -> None:
    settings = ServiceSettings.from_env()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    service = ModelService(settings.model_path)
    api, metrics, _ = create_servers(settings, service)

    if settings.auto_bootstrap and not service.ready():

        def bootstrap() -> None:
            try:
                service.bootstrap(settings.bootstrap_profile)
            except Exception:
                logger.exception("Model bootstrap failed")

        threading.Thread(target=bootstrap, name="ml-bootstrap", daemon=True).start()

    threading.Thread(
        target=metrics.serve_forever, name="ml-metrics", daemon=True
    ).start()

    def stop(*_: Any) -> None:
        threading.Thread(target=api.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    logger.info(
        "ML service listening on :%d (metrics :%d)",
        settings.port,
        settings.metrics_port,
    )
    try:
        api.serve_forever()
    finally:
        metrics.shutdown()
        api.server_close()
        metrics.server_close()
        service.shutdown()


if __name__ == "__main__":
    main()
