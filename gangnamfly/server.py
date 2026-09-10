"""Loopback-only local UI; allowlisted commands and no general filesystem API."""

import json
import mimetypes
import queue
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from .config import ROOT
from .evidence import bundle


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True


def handler(runtime, port, web=ROOT / "web/dist"):
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    origins = {f"http://{host}" for host in hosts}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, status, body, content_type="application/json", compressed=False):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
            )
            self.send_header("Cache-Control", "no-store" if self.path.startswith("/api/") else "no-cache")
            if compressed:
                self.send_header("Content-Encoding", "gzip")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def json(self, status, body):
            self.send(status, json.dumps(body, allow_nan=False).encode())

        def allowed(self):
            if self.headers.get("Host") not in hosts:
                self.json(403, {"error": "Host inválido"})
                return False
            if self.headers.get("Origin") not in origins | {None}:
                self.json(403, {"error": "Origen inválido"})
                return False
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                self.json(403, {"error": "Solicitud externa rechazada"})
                return False
            return True

        def do_GET(self):
            if not self.allowed():
                return
            route = urlsplit(self.path).path
            if route == "/api/state":
                return self.json(200, runtime.read())
            if route == "/api/demo":
                if runtime.demo is None:
                    return self.json(
                        503, {"error": getattr(runtime, "demo_error", None) or "Referencia cargando"}
                    )
                return self.send(200, runtime.demo, compressed=True)
            if route.startswith("/api/evidence/"):
                try:
                    payload = bundle(runtime.root, route.removeprefix("/api/evidence/"))
                except (ValueError, OSError):
                    return self.json(404, {"error": "Evidencia no disponible"})
                return self.send(200, payload, "application/zip")
            if route == "/api/model":
                if runtime.model is None:
                    return self.json(503, {"error": "Modelo cargando"})
                return self.send(200, runtime.model, compressed=True)
            if route == "/":
                target = web / "index.html"
            elif route.startswith("/assets/") and ".." not in route and "%" not in route:
                target = web / route.lstrip("/")
            else:
                return self.json(404, {"error": "No encontrado"})
            if not target.is_file() or not target.resolve().is_relative_to(web.resolve()):
                return self.json(404, {"error": "Frontend no compilado; ejecutá npm run build en web/"})
            return self.send(
                200, target.read_bytes(), mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            )

        def do_POST(self):
            if not self.allowed():
                return
            if self.path != "/api/command":
                return self.json(404, {"error": "No encontrado"})
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.json(415, {"error": "Se requiere application/json"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 512:
                    raise ValueError("Tamaño de solicitud inválido")
                self.connection.settimeout(3)
                value = json.loads(self.rfile.read(length))
                if (
                    not isinstance(value, dict)
                    or set(value) - {"action", "episode"}
                    or not isinstance(value.get("action"), str)
                ):
                    raise ValueError("Comando inválido")
                runtime.submit(value["action"], value.get("episode"))
            except (ValueError, TypeError, TimeoutError) as exc:
                return self.json(400, {"error": str(exc)})
            except queue.Full:
                return self.json(429, {"error": "Hay comandos pendientes; esperá un momento"})
            return self.json(202, {"ok": True})

    return Handler
