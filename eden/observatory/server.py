from __future__ import annotations

import http.server
import json
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..utils import now_utc


SERVER_INFO_FILENAME = ".eden_observatory.json"
API_VERSION = 2


class _ThreadingHTTPServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class _ObservatoryHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(
        self,
        *args: Any,
        directory: str,
        service: Any | None,
        status_provider: Callable[[], dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        self._service = service
        self._status_provider = status_provider
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - noisy stdio suppression
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == f"/{SERVER_INFO_FILENAME}":
            self._send_json(self._status_provider())
            return
        if parsed.path == "/api/status":
            self._send_json({"ok": True, "status": self._status_provider()})
            return
        if parsed.path.startswith("/api/experiments/"):
            self._handle_api_get(parsed)
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if not parsed.path.startswith("/api/experiments/"):
            self.send_error(404, "Unknown API path.")
            return
        if self._service is None:
            self._send_json({"error": "Live observatory API unavailable."}, status=503)
            return
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 4:
            self._send_json({"error": "Malformed API path."}, status=404)
            return
        _, _, experiment_id, action_name = parts[:4]
        body = self._read_json_body()
        try:
            if action_name == "preview":
                result = self._service.preview_action(
                    experiment_id=experiment_id,
                    session_id=body.get("session_id"),
                    turn_id=body.get("turn_id"),
                    action=body.get("action", body),
                )
            elif action_name == "commit":
                result = self._service.commit_action(
                    experiment_id=experiment_id,
                    session_id=body.get("session_id"),
                    turn_id=body.get("turn_id"),
                    action=body.get("action", body),
                )
            elif action_name == "revert":
                result = self._service.revert_event(
                    experiment_id=experiment_id,
                    session_id=body.get("session_id"),
                    turn_id=body.get("turn_id"),
                    event_id=str(body.get("event_id", "")).strip(),
                )
            else:
                self._send_json({"error": f"Unknown action '{action_name}'."}, status=404)
                return
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
            return
        except KeyError as exc:
            self._send_json({"error": str(exc)}, status=404)
            return
        except Exception as exc:  # pragma: no cover - defensive API guard
            self._send_json({"error": f"Unhandled observatory API failure: {exc}"}, status=500)
            return
        self._send_json(result)

    def _handle_api_get(self, parsed: urllib.parse.ParseResult) -> None:
        if self._service is None:
            self._send_json({"error": "Live observatory API unavailable."}, status=503)
            return
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 4:
            self._send_json({"error": "Malformed API path."}, status=404)
            return
        _, _, experiment_id, action_name = parts[:4]
        query = urllib.parse.parse_qs(parsed.query)
        session_id = query.get("session_id", [None])[0]
        if action_name == "payload":
            _, payload = self._service.refresh_exports(experiment_id=experiment_id, session_id=session_id)
            self._send_json(payload)
            return
        if action_name == "measurement-events":
            _, payload = self._service.refresh_exports(experiment_id=experiment_id, session_id=session_id)
            self._send_json(payload["measurements"])
            return
        self._send_json({"error": f"Unknown action '{action_name}'."}, status=404)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
        encoded = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)


@dataclass(slots=True)
class ObservatoryStatus:
    host: str
    port: int
    root: str
    url: str
    info_url: str
    server_type: str
    started_at: str
    reused_existing: bool
    owned_by_process: bool
    pid: int
    api_version: int = API_VERSION
    capabilities: dict[str, Any] = field(default_factory=dict)


class ObservatoryServer:
    def __init__(
        self,
        root: Path,
        port: int,
        *,
        host: str = "127.0.0.1",
        port_span: int = 24,
        service: Any | None = None,
    ) -> None:
        self.root = root.resolve()
        self.host = host
        self.port = port
        self.port_span = port_span
        self.service = service
        self._thread: threading.Thread | None = None
        self._httpd: _ThreadingHTTPServer | None = None
        self._status: ObservatoryStatus | None = None

    @property
    def info_path(self) -> Path:
        return self.root / SERVER_INFO_FILENAME

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and self._httpd is not None

    def start(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        reuse_existing: bool = True,
    ) -> ObservatoryStatus:
        target_host = host or self.host
        target_port = port or self.port
        if self.running and self._status is not None:
            return self._status

        self.root.mkdir(parents=True, exist_ok=True)

        if reuse_existing:
            reused = self._probe_same_root(host=target_host, port=target_port)
            if reused is None:
                reused = self._probe_from_info_file(expected_root=self.root)
            if reused is not None:
                self._status = reused
                return reused

        actual_port = self._discover_port(target_host, target_port)
        handler = self._make_handler(self.root)
        self._httpd = _ThreadingHTTPServer((target_host, actual_port), handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        self._status = ObservatoryStatus(
            host=target_host,
            port=actual_port,
            root=str(self.root),
            url=f"http://{target_host}:{actual_port}/",
            info_url=f"http://{target_host}:{actual_port}/{SERVER_INFO_FILENAME}",
            server_type="eden_observatory",
            started_at=now_utc(),
            reused_existing=False,
            owned_by_process=True,
            pid=self._process_id(),
            api_version=API_VERSION,
            capabilities={
                "preview": self.service is not None,
                "commit": self.service is not None,
                "revert": self.service is not None,
                "measurement_events": self.service is not None,
            },
        )
        self._write_info_file(self._status)
        return self._status

    def stop(self) -> bool:
        was_owned = self.running and self._httpd is not None
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if was_owned and self.info_path.exists():
            try:
                self.info_path.unlink()
            except OSError:
                pass
        self._status = None
        return was_owned

    def status(self) -> ObservatoryStatus | None:
        if self.running and self._status is not None:
            return self._status
        return self._probe_from_info_file(expected_root=self.root)

    def _process_id(self) -> int:
        import os

        return os.getpid()

    def _status_payload(self) -> dict[str, Any]:
        if self._status is None:
            return {
                "root": str(self.root),
                "server_type": "eden_observatory",
                "api_version": API_VERSION,
                "capabilities": {
                    "preview": self.service is not None,
                    "commit": self.service is not None,
                    "revert": self.service is not None,
                    "measurement_events": self.service is not None,
                },
            }
        return asdict(self._status)

    def _make_handler(self, root: Path):
        def factory(*args: Any, **kwargs: Any):
            return _ObservatoryHandler(
                *args,
                directory=str(root),
                service=self.service,
                status_provider=self._status_payload,
                **kwargs,
            )

        return factory

    def _is_port_available(self, host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                return False
        return True

    def _discover_port(self, host: str, preferred_port: int) -> int:
        for candidate in range(preferred_port, preferred_port + self.port_span + 1):
            if self._is_port_available(host, candidate):
                return candidate
        raise RuntimeError(
            f"No free observatory port found in {host}:{preferred_port}-{preferred_port + self.port_span}."
        )

    def _probe_same_root(self, *, host: str, port: int) -> ObservatoryStatus | None:
        return self._probe_remote_info(host=host, port=port, expected_root=self.root)

    def _probe_from_info_file(self, *, expected_root: Path) -> ObservatoryStatus | None:
        if not self.info_path.exists():
            return None
        try:
            payload = json.loads(self.info_path.read_text(encoding="utf-8"))
            host = str(payload["host"])
            port = int(payload["port"])
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return None
        return self._probe_remote_info(host=host, port=port, expected_root=expected_root)

    def _probe_remote_info(self, *, host: str, port: int, expected_root: Path) -> ObservatoryStatus | None:
        url = f"http://{host}:{port}/{SERVER_INFO_FILENAME}"
        try:
            with urllib.request.urlopen(url, timeout=0.35) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            return None
        root = Path(str(payload.get("root", ""))).resolve()
        if payload.get("server_type") != "eden_observatory" or root != expected_root.resolve():
            return None
        if int(payload.get("api_version", 0) or 0) < API_VERSION:
            return None
        return ObservatoryStatus(
            host=str(payload["host"]),
            port=int(payload["port"]),
            root=str(root),
            url=str(payload["url"]),
            info_url=str(payload["info_url"]),
            server_type=str(payload["server_type"]),
            started_at=str(payload["started_at"]),
            reused_existing=True,
            owned_by_process=False,
            pid=int(payload.get("pid", 0) or 0),
            api_version=int(payload.get("api_version", API_VERSION) or API_VERSION),
            capabilities=dict(payload.get("capabilities", {})),
        )

    def _write_info_file(self, status: ObservatoryStatus) -> None:
        self.info_path.write_text(json.dumps(asdict(status), indent=2), encoding="utf-8")
