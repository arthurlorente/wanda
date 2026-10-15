"""Loopback-only V0 HTTP boundary. No audio, chat or credentials are logged."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import hmac
import json
import math
import mimetypes
import secrets
from socketserver import TCPServer
import threading
from urllib.parse import urlsplit

from . import __version__
from .config import Config, ROOT
from .memory import MemoryStore
from .home import HomeService, MockHomeAdapter, HomeAssistantAdapter
from .persona import PERSONA_VERSION, demo_reply
from .voice import VoiceProvider

OWNER = "local-owner"


class ApiError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


def string(data, key, limit=2000, default=None):
    value = data.get(key, default)
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{key} must be nonempty text, at most {limit} characters.")
    return value.strip()


def boolean(data, key, default=None):
    value = data.get(key, default)
    if type(value) is not bool:
        raise ValueError(f"{key} must be true or false.")
    return value


def expiry(data):
    value = data.get("expires_at")
    if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value <= 0):
        raise ValueError("expires_at must be a valid Unix timestamp or null.")
    return value


class Application:
    def __init__(self, config: Config, memory=None, home=None, voice=None):
        self.config = config
        config.prepare()
        self.memory = memory or MemoryStore(config.data_dir / "memory.sqlite3")
        adapter = None
        if home is None:
            adapter = MockHomeAdapter() if config.home_mode == "mock" else HomeAssistantAdapter(
                config.home_url, config.home_token, config.home_entities,
                allow_insecure_http=config.home_allow_insecure_http)
        self.home = home or HomeService(adapter)
        self.voice = voice or VoiceProvider(config.api_key, config.voice_model)
        self.token = secrets.token_urlsafe(32)
        self.voice_lock = threading.Lock()

    def dispatch(self, method, path, data):
        if method == "GET" and path == "/api/status":
            return {
                "version": __version__, "mode": "demo",
                "memory_enabled": self.memory.is_enabled(OWNER),
                "voice": {"configured": self.config.voice_enabled and bool(self.config.api_key),
                          "provider": "openai", "model": self.config.voice_model},
                "home": {"mode": self.config.home_mode}, "persona_version": PERSONA_VERSION,
            }
        if method == "POST" and path == "/api/chat":
            text = string(data, "text", 4000)
            language = string(data, "language", 16, "en")
            tone = string(data, "tone", 16, "warm")
            if language not in ("en", "pt", "es") or tone not in ("warm", "neutral"):
                raise ValueError("Choose a supported demo language and tone.")
            extraction = self.memory.extract(OWNER, text)
            reply = demo_reply(text, language=language, tone=tone)
            # Local explicit recall never sends saved facts to a model or provider.
            if any(word in text.casefold() for word in ("what do you remember", "minhas memórias", "qué recuerdas")):
                records = self.memory.recall(OWNER)
                prefix = {"en": "Your enabled local memories: ", "pt": "Suas memórias locais ativas: ", "es": "Tus recuerdos locales activos: "}[language]
                empty = {"en": "There are no enabled memories to recall. You control them in Memory.", "pt": "Não há memórias ativas. Você as controla em Memória.", "es": "No hay recuerdos activos. Tú los controlas en Memoria."}[language]
                reply = prefix + "; ".join(item["text"] for item in records[:8]) if records else empty
            return {"reply": reply, "mode": "demo", "memory_saved": extraction["saved"],
                    "memory_candidates": extraction["candidates"], "suggestions": []}
        if path == "/api/memory":
            if method == "GET":
                return {"enabled": self.memory.is_enabled(OWNER), "memories": self.memory.list_memories(OWNER)}
            if method == "DELETE":
                self.memory.clear(OWNER)
                return {"ok": True}
            if method == "POST":
                return self.memory.save(OWNER, string(data, "text"), string(data, "category", 32, "preference"),
                                        approved=boolean(data, "approved", False), expires_at=expiry(data))
        if method == "POST" and path == "/api/memory/consent":
            enabled = boolean(data, "enabled")
            self.memory.set_enabled(OWNER, enabled)
            return {"enabled": enabled}
        if method == "GET" and path == "/api/memory/export":
            return self.memory.export(OWNER)
        if method == "GET" and path == "/api/memory/backup":
            return self.memory.backup(OWNER)
        if method == "POST" and path == "/api/memory/restore/preview":
            if set(data) != {"backup"}:
                raise ValueError("Provide only the backup to preview.")
            return self.memory.restore_preview(OWNER, data["backup"])
        if method == "POST" and path == "/api/memory/restore":
            if set(data) != {"backup", "approved"}:
                raise ValueError("Explicit local restore approval is required.")
            return self.memory.restore(OWNER, data["backup"], approved=boolean(data, "approved"))
        if path.startswith("/api/memory/") and method in ("PATCH", "DELETE"):
            memory_id = path.removeprefix("/api/memory/")
            if method == "DELETE":
                self.memory.delete(OWNER, memory_id)
                return {"ok": True}
            return self.memory.update(OWNER, memory_id, string(data, "text"), string(data, "category", 32),
                                      approved=boolean(data, "approved", False), expires_at=expiry(data))
        if path == "/api/disclosures":
            if method == "GET":
                return {"grants": self.memory.list_grants(OWNER)}
            if method == "POST":
                return self.memory.set_grant(OWNER, string(data, "provider", 32), string(data, "category", 32),
                                             boolean(data, "allowed"), one_time=boolean(data, "one_time", False),
                                             expires_at=expiry(data))
        if method == "DELETE" and path.startswith("/api/disclosures/"):
            self.memory.revoke_grant(OWNER, path.removeprefix("/api/disclosures/"))
            return {"ok": True}
        if method == "GET" and path == "/api/home":
            return self.home.snapshot(OWNER)
        if method == "POST" and path == "/api/home/grants":
            return self.home.grant(OWNER, string(data, "entity_id", 100), string(data, "action", 32),
                                   confirmation=boolean(data, "confirmation", True), expires_at=expiry(data))
        if method == "DELETE" and path.startswith("/api/home/grants/"):
            self.home.revoke(OWNER, path.removeprefix("/api/home/grants/"))
            return {"ok": True}
        if method == "POST" and path == "/api/home/action":
            confirmation = data.get("confirmation_id")
            if confirmation is not None:
                confirmation = string(data, "confirmation_id", 200)
            return self.home.act(OWNER, string(data, "entity_id", 100), string(data, "action", 32),
                                 string(data, "request_id", 100), confirmation_id=confirmation)
        if method == "POST" and path == "/api/home/outage":
            self.home.set_outage(boolean(data, "offline"))
            return {"ok": True}
        if method == "POST" and path == "/api/voice/session":
            if not self.config.voice_enabled or not self.config.api_key:
                raise ApiError(503, "voice_not_configured", "Live cloud voice is not configured. Local demo remains available.")
            if not boolean(data, "audio_consent", False):
                raise ApiError(403, "audio_consent_required", "Review and accept the cloud audio disclosure for this session.")
            sdp = string(data, "sdp", 100000)
            if not self.voice_lock.acquire(blocking=False):
                raise ApiError(429, "voice_busy", "A voice connection is already starting.")
            try:
                return {"sdp": self.voice.create_session(sdp)}
            finally:
                self.voice_lock.release()
        raise ApiError(404, "not_found", "This action does not exist.")

    def close(self):
        self.memory.close()


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = True

    def __init__(self, app, port=None):
        self.app = app
        self.slots = threading.BoundedSemaphore(16)
        super().__init__(("127.0.0.1", app.config.port if port is None else port), Handler)

    def server_bind(self):
        # HTTPServer performs reverse DNS here, which can block offline startup.
        # This listener always uses the numeric loopback address.
        TCPServer.server_bind(self)
        self.server_name = "localhost"
        self.server_port = self.server_address[1]

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        super().process_request(request, client_address)

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version = "Wanda/0.1"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *_):
        pass  # Never log request bodies, tokens, paths containing user text, or audio.

    def respond(self, status, payload, content_type="application/json; charset=utf-8"):
        if not isinstance(payload, bytes):
            payload = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Permissions-Policy", "microphone=(self), camera=(), geolocation=()")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self' https://api.openai.com; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def handle_request(self):
        try:
            port = self.server.server_address[1]
            host = self.headers.get("Host", "")
            allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
            if host not in allowed_hosts:
                raise ApiError(403, "invalid_host", "Use the local launcher address.")
            origin = self.headers.get("Origin")
            if origin is not None and origin not in {f"http://{x}" for x in allowed_hosts}:
                raise ApiError(403, "invalid_origin", "Cross-site requests are not allowed.")
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                raise ApiError(403, "cross_site", "Cross-site requests are not allowed.")
            parsed = urlsplit(self.path)
            path = parsed.path
            if self.command == "GET" and path == "/health":
                self.respond(200, {"service": "wanda", "version": __version__})
                return
            if path.startswith("/api/"):
                credential = self.headers.get("Authorization", "")
                if not hmac.compare_digest(credential, "Bearer " + self.server.app.token):
                    raise ApiError(401, "unauthorized", "Open Wanda using Start Wanda to unlock this browser.")
                data = {}
                if self.command in ("POST", "PATCH", "DELETE"):
                    if self.headers.get("Transfer-Encoding"):
                        raise ApiError(400, "invalid_body", "Chunked request bodies are not supported.")
                    length = int(self.headers.get("Content-Length", "0"))
                    limit = 8 * 1024 * 1024 if self.command == "POST" and path in {
                        "/api/memory/restore/preview", "/api/memory/restore"
                    } else 131072
                    if length < 0 or length > limit:
                        raise ApiError(413, "body_too_large", "Request exceeds the local size limit.")
                    if length:
                        if self.headers.get_content_type() != "application/json":
                            raise ApiError(415, "json_required", "Send JSON for this action.")
                        data = json.loads(self.rfile.read(length), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Invalid JSON number.")))
                        if not isinstance(data, dict):
                            raise ValueError("Request must be a JSON object.")
                if self.command == "POST" and path == "/api/shutdown":
                    self.respond(200, {"ok": True})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
                result = self.server.app.dispatch(self.command, path, data)
                self.respond(200, result)
                return
            if self.command != "GET" or path not in ("/", "/index.html", "/app.js", "/backup.js", "/styles.css"):
                raise ApiError(404, "not_found", "Page not found.")
            file = ROOT / "web" / ("index.html" if path == "/" else path[1:])
            self.respond(200, file.read_bytes(), (mimetypes.guess_type(str(file))[0] or "text/plain") + "; charset=utf-8")
        except ApiError as error:
            self.respond(error.status, {"error": error.message, "code": error.code})
        except (ValueError, TypeError, KeyError, UnicodeError):
            self.respond(400, {"error": "Invalid request. Check the fields and try again.", "code": "invalid_request"})
        except PermissionError:
            self.respond(403, {"error": "This action needs consent or an appropriate permission.", "code": "permission_required"})
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            return
        except Exception:
            self.respond(503, {"error": "That service is unavailable. Your local controls remain available; no automatic retry was made.", "code": "unavailable"})

    do_GET = handle_request
    do_POST = handle_request
    do_PATCH = handle_request
    do_DELETE = handle_request
    do_OPTIONS = handle_request
