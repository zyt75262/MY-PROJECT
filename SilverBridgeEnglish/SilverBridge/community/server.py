"""JSON API with opt-in LAN sharing without a login gate.

One server and SQLite database serve all devices. This pilot server is not a
production hosting platform. No third-party services are called.
"""

from __future__ import annotations

import json
import ipaddress
import logging
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import __version__
from .errors import ValidationError
from .storage import RecordError, Storage

LOGGER = logging.getLogger("community")
MAX_BODY = 3_000_000


def reject_nonfinite(value: str):
    raise ValueError(f"Non-finite JSON number: {value}")


def build_server(project_root: Path, database_path: Path, port: int = 8765,
                 host: str = "127.0.0.1",
                 public_host: str | None = None) -> ThreadingHTTPServer:
    shared_mode = host != "127.0.0.1"
    project_root = Path(project_root).resolve()
    storage = Storage(database_path)
    def visible_stories():
        return [story for story in storage.stories()
                if not shared_mode or story["publication_state"] == "community_shared"]
    static_files = {
        "/": ("index.html", "text/html; charset=utf-8"),
        "/index.html": ("index.html", "text/html; charset=utf-8"),
        "/app.js": ("app.js", "text/javascript; charset=utf-8"),
        "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    }

    class Handler(BaseHTTPRequestHandler):
        server_version = "CommunityApps/" + __version__
        sys_version = ""

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, format, *args):
            LOGGER.info(format, *args)

        def send_bytes(self, body: bytes, content_type: str, status: int = 200, download: bool = False):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if download:
                self.send_header("Content-Disposition", 'attachment; filename="brightbite-plan.txt"')
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, data: dict | list, status: int = 200):
            self.send_bytes(json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8"), "application/json; charset=utf-8", status)

        def local_request(self, write: bool = False):
            allowed_hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            host = self.headers.get("Host", "")
            if public_host:
                allowed_hosts.add(public_host)
            if self.server.server_address[0] != "127.0.0.1":
                try:
                    parsed_host = urlsplit("http://" + host)
                    address = ipaddress.ip_address(parsed_host.hostname or "")
                    if address.version == 4 and parsed_host.port == self.server.server_port and (address.is_private or address.is_loopback):
                        allowed_hosts.add(host)
                except ValueError:
                    pass
            if host not in allowed_hosts:
                raise RecordError("Use an address listed in the startup window.", 403)
            origin = self.headers.get("Origin")
            if origin and origin not in {"http://" + host, "https://" + host}:
                raise RecordError("Requests from other websites are not allowed.", 403)
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                raise RecordError("Cross-site requests are not allowed.", 403)
            if write and self.headers.get("X-Local-Request") != "1":
                raise RecordError("Please use the application page to perform this action.", 403)

        def read_json(self) -> dict:
            self.local_request(write=True)
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise RecordError("The request must use application/json.", 415)
            if self.headers.get("Transfer-Encoding"):
                raise RecordError("Chunked uploads are not supported.", 400)
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as error:
                raise RecordError("Invalid request length.", 400) from error
            if not 0 < length <= MAX_BODY:
                raise RecordError("The request is empty or its attachment is too large.", 413)
            try:
                raw = self.rfile.read(length)
                data = json.loads(raw.decode("utf-8"), parse_constant=reject_nonfinite)
            except (UnicodeError, ValueError) as error:
                raise RecordError("Invalid JSON.", 400) from error
            if not isinstance(data, dict):
                raise RecordError("The JSON root must be an object.", 400)
            return data

        def do_GET(self):
            try:
                self.local_request()
                parsed = urlsplit(self.path)
                path = parsed.path
                if path in static_files:
                    name, mime = static_files[path]
                    self.send_bytes((project_root / "web" / name).read_bytes(), mime)
                elif path == "/api/health":
                    self.send_json({"ok": True, "version": __version__, "mode": "shared" if shared_mode else "local_demo", "app": "silverbridge"})
                elif path == "/api/shared":
                    self.send_json({"tickets": storage.tickets(), "stories": visible_stories()})
                elif path == "/api/state":
                    self.send_json({"tickets": storage.tickets(), "stories": visible_stories()})
                else:
                    raise RecordError("Page or API route not found.", 404)
            except (ValidationError, RecordError) as error:
                self.send_json({"error": str(error)}, getattr(error, "status", 400))
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                LOGGER.exception("GET request failed")
                self.send_json({"error": "The local server encountered an error. Check its startup window."}, 500)

        def do_POST(self):
            try:
                payload = self.read_json()
                path = urlsplit(self.path).path
                if path == "/api/tickets":
                    self.send_json(storage.create_ticket(payload), 201)
                elif match := re.fullmatch(r"/api/tickets/(\d+)/(claim|reply|resolve|reopen)", path):
                    self.send_json(storage.transition_ticket(int(match[1]), match[2], payload))
                elif path == "/api/stories":
                    if shared_mode and payload.get("share") is not True:
                        raise ValidationError("Confirm the storyteller\'s permission before sharing this story.")
                    self.send_json(storage.create_story(payload), 201)
                else:
                    raise RecordError("API route not found.", 404)
            except (ValidationError, RecordError) as error:
                self.send_json({"error": str(error)}, getattr(error, "status", 400))
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                LOGGER.exception("POST request failed")
                self.send_json({"error": "The local server encountered an error. Check its startup window."}, 500)

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server
