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
from .locale import label
from .planner import ALLERGENS, ValidationError, generate_plan, load_recipes, replace_recipe, replacement_candidates
from .storage import RecordError, Storage
from .health import NOTICE, day_health, explain_plan, ingredient_health

LOGGER = logging.getLogger("community")
MAX_BODY = 3_000_000


def reject_nonfinite(value: str):
    raise ValueError(f"Non-finite JSON number: {value}")


def export_plan(plan: dict, by_id: dict) -> str:
    lines = ["BrightBite - Demonstration meal plan", "Demo recipes and estimated CNY prices; not a medical diet.", ""]
    for index, day in enumerate(plan["days"], 1):
        lines.append(f"Day {index}: CNY {day['cost_cents']/100:.2f}")
        for meal in day["meals"]:
            names = ", ".join(by_id[item].name for item in meal["ids"])
            lines.append(f"{label(meal['slot'])}: {names} (CNY {meal['cost_cents']/100:.2f})")
        lines.append("Body functions and health context:")
        for profile in day_health(day, by_id):
            lines.append(f"- {profile['part']}: {profile['function']}. Ingredients: {', '.join(profile['matched_ingredients'])}.")
            lines.append(f"  {profile['concern']}: {profile['condition_note']}")
        lines.append("")
    lines.append(NOTICE)
    lines.append("Exclusions: " + (", ".join(label(x) for x in plan["options"]["allergies"]) or "None"))
    lines.append("Check actual ingredients, seasonings, allergens and preparation conditions.")
    return "\n".join(lines)


def build_server(project_root: Path, database_path: Path, port: int = 8766,
                 host: str = "127.0.0.1",
                 public_host: str | None = None) -> ThreadingHTTPServer:
    shared_mode = host != "127.0.0.1"
    project_root = Path(project_root).resolve()
    recipes = load_recipes(project_root / "data" / "recipes_demo.json")
    by_id = {recipe.id: recipe for recipe in recipes}
    storage = Storage(database_path)
    catalog = json.loads((project_root / "data" / "recipes_source.json").read_text(encoding="utf-8"))
    catalog["recipes"] = [{**item, "health_support": ingredient_health(item.get("ingredients", [])) if item.get("edible") else []}
                           for item in catalog["recipes"]]
    catalog_ids = {item["id"] for item in catalog["recipes"]}
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
                    self.send_json({"ok": True, "version": __version__, "mode": "shared" if shared_mode else "local_demo", "app": "brightbite"})
                elif path == "/api/state":
                    self.send_json({
                        "recipes": [r.to_dict() for r in recipes], "allergens": list(ALLERGENS),
                        "plan": explain_plan(storage.latest_plan(), by_id), "favorites": storage.favorites(),
                        "source_recipes": catalog["recipes"], "catalog_info": catalog["info"], "health_notice": NOTICE,
                    })
                elif match := re.fullmatch(r"/api/plans/([a-f0-9]{32})/(replacements|export)", path):
                    plan = storage.get_plan(match[1])
                    if match[2] == "export":
                        self.send_bytes(export_plan(plan, by_id).encode("utf-8"), "text/plain; charset=utf-8", download=True)
                    else:
                        query = parse_qs(parsed.query)
                        try:
                            indices = [int(query[key][0]) for key in ("day", "meal", "position")]
                        except (ValueError, KeyError, IndexError) as error:
                            raise ValidationError("Specify a valid position in the meal plan.") from error
                        items = replacement_candidates(recipes, plan, *indices)
                        self.send_json({"recipes": [r.to_dict() for r in items]})
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
                if path == "/api/plans":
                    plan = generate_plan(recipes, payload)
                    self.send_json(explain_plan(storage.save_plan(plan), by_id), 201)
                elif match := re.fullmatch(r"/api/plans/([a-f0-9]{32})/(replace|feedback)", path):
                    if match[2] == "feedback":
                        self.send_json(explain_plan(storage.set_feedback(match[1], payload.get("feedback", "")), by_id))
                    else:
                        def change(plan):
                            replace_recipe(recipes, plan, payload.get("day"), payload.get("meal"), payload.get("position"), payload.get("recipe_id"))
                        self.send_json(explain_plan(storage.change_plan(match[1], change), by_id))
                elif match := re.fullmatch(r"/api/favorites/([a-z0-9_-]+)", path):
                    if match[1] not in by_id and match[1] not in catalog_ids:
                        raise RecordError("Recipe not found.", 404)
                    self.send_json({"favorites": storage.set_favorite(match[1], payload.get("saved"))})
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
