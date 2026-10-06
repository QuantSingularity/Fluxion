from __future__ import annotations

import json
import logging
import time
from http.server import BaseHTTPRequestHandler
from typing import Any, Dict

from ml_models.data.features import InputError
from ml_models.serving.app import MAX_BODY_BYTES, Application, HttpError
from ml_models.serving.service import ModelNotReady

logger = logging.getLogger("ml-service")


def make_handler(app: Application):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _send(self, status: int, payload: Any) -> None:
            body = json.dumps(payload, default=str).encode("utf-8")
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                logger.debug("Client disconnected before response was sent")

        def _read_body(self) -> Dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise HttpError(400, "Invalid Content-Length")
            if length > MAX_BODY_BYTES:
                raise HttpError(413, "Request body too large")
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                raise HttpError(400, "Body must be valid JSON")
            if not isinstance(data, dict):
                raise HttpError(400, "Body must be a JSON object")
            return data

        def _handle(self, method: str) -> None:
            started = time.perf_counter()
            path = self.path.split("?", 1)[0]
            status = 500
            try:
                if method == "GET" and path == "/health":
                    status = 200
                    self._send(status, app.health())
                    return
                if method == "GET" and path == "/ready":
                    status, payload = app.readiness()
                    self._send(status, payload)
                    return
                if method == "GET" and path == "/":
                    status = 200
                    self._send(status, {"service": "fluxion-ml", "status": "ok"})
                    return
                if not app.authorized(method, path, self.headers.get("X-API-Key")):
                    status = 401
                    self._send(status, {"error": "Unauthorized"})
                    return
                handler = app.routes.get((method, path))
                if handler is None:
                    status = 404
                    self._send(status, {"error": "Not found"})
                    return
                body = self._read_body() if method == "POST" else {}
                rid = self.headers.get("X-Request-ID")
                status, payload = handler(body, rid)
                self._send(status, payload)
            except HttpError as exc:
                status = exc.status
                self._send(status, {"error": exc.message})
            except InputError as exc:
                status = 422
                self._send(status, {"error": str(exc)})
            except ModelNotReady as exc:
                status = 503
                self._send(status, {"error": str(exc)})
            except ValueError as exc:
                status = 400
                self._send(status, {"error": str(exc)})
            except Exception:
                logger.exception("Unhandled error on %s %s", method, path)
                status = 500
                self._send(status, {"error": "Internal server error"})
            finally:
                app.metrics.observe(method, path, status, time.perf_counter() - started)

        def do_GET(self) -> None:
            self._handle("GET")

        def do_POST(self) -> None:
            self._handle("POST")

        def log_message(self, fmt: str, *args: Any) -> None:
            logger.debug("%s - %s", self.address_string(), fmt % args)

    return Handler
