"""Explicitly authorized, bounded synthetic Realtime API validation.

Importing this module performs no configuration read or network request. Only
the CLI's ``--allow-paid`` path loads private configuration. The browser child
receives a loopback capability, never the provider key. Do not run from CI.
"""

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.live_test_budget import DEFAULT_DEADLINE, TestBudget
from wanda.config import Config, ROOT
from wanda.server import Application, LocalServer
from wanda.voice import ENDPOINT, VoiceProvider


MODEL = "gpt-realtime-2.1"
RESERVE_MICROUSD = 3_000_000
TOTAL_LIMIT_MICROUSD = 10_000_000
MAX_ATTEMPTS = 2
CHILD_SCRIPT = Path(__file__).with_name("live-voice-check.cjs")
_CALL_ID = re.compile(r"rtc_[A-Za-z0-9_-]{1,128}\Z")
_SAFE_CODE = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_SAFE_PHASE = re.compile(r"[a-z][a-z0-9_]{0,31}\Z")
_PROVIDER_ERROR_CODES = frozenset({
    "invalid_request_error", "invalid_value", "invalid_type", "invalid_model",
    "model_not_found", "authentication_error", "invalid_api_key",
    "insufficient_quota", "rate_limit_exceeded", "unsupported_value", "invalid_sdp",
})
_PROVIDER_ERROR_PARAMS = frozenset({
    "sdp", "session", "model", "session.model", "session.type",
    "session.audio", "session.audio.input", "session.audio.output",
    "session.output_modalities", "session.max_output_tokens", "session.reasoning",
    "session.instructions", "session.tools", "session.tool_choice", "session.tracing",
})
_CHILD_ENV = frozenset({
    "PATH", "HOME", "TMPDIR", "TMP", "TEMP", "NODE_PATH", "WANDA_TEST_BROWSER",
    "LANG", "LC_ALL", "LC_CTYPE", "TZ", "SYSTEMROOT", "WINDIR", "COMSPEC",
    "PATHEXT", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "PROGRAMFILES",
})


def call_id_from_location(location):
    """Accept only a canonical OpenAI Realtime call Location, never a URL pivot."""
    if not isinstance(location, str) or len(location) > 256:
        raise ValueError("Invalid Realtime call location.")
    parsed = urllib.parse.urlsplit(location)
    if parsed.scheme or parsed.netloc:
        if (parsed.scheme != "https" or parsed.hostname != "api.openai.com" or
                parsed.port is not None or parsed.username or parsed.password):
            raise ValueError("Invalid Realtime call location.")
    if parsed.query or parsed.fragment:
        raise ValueError("Invalid Realtime call location.")
    prefix = "/v1/realtime/calls/"
    if not parsed.path.startswith(prefix):
        raise ValueError("Invalid Realtime call location.")
    identifier = parsed.path[len(prefix):]
    if not _CALL_ID.fullmatch(identifier):
        raise ValueError("Invalid Realtime call location.")
    if parsed.path != prefix + identifier or (not parsed.scheme and location != prefix + identifier):
        raise ValueError("Invalid Realtime call location.")
    return identifier


def child_environment(source=None):
    source = os.environ if source is None else source
    return {key: value for key, value in source.items() if key in _CHILD_ENV and isinstance(value, str)}


def validate_live_config(config):
    if (not isinstance(config, Config) or config.voice_enabled is not True or
            config.voice_model != MODEL or not isinstance(config.api_key, str) or
            not config.api_key or any(char in config.api_key for char in "\r\n")):
        raise ValueError("Live voice test configuration is unavailable.")


def _safe_count(value, maximum):
    return value if type(value) is int and 0 <= value <= maximum else None


def safe_provider_error(error):
    """Extract only preapproved diagnostic labels from a bounded provider body."""
    result = {"provider_error_code": None, "provider_error_param": None,
              "provider_error_hint": None}
    try:
        raw = error.read(10_241)
        if len(raw) > 10_240:
            return result
        parsed = json.loads(raw.decode("utf-8"))
        detail = parsed.get("error") if type(parsed) is dict else None
        if type(detail) is not dict:
            return result
        code = detail.get("code")
        if code is None:
            code = detail.get("type")
        if type(code) is str and code in _PROVIDER_ERROR_CODES:
            result["provider_error_code"] = code
        param = detail.get("param")
        if type(param) is str and param in _PROVIDER_ERROR_PARAMS:
            result["provider_error_param"] = param
        message = detail.get("message")
        if type(message) is str and message.startswith("Failed to parse SDP"):
            result["provider_error_hint"] = "sdp_parse_failed"
    except (OSError, UnicodeError, ValueError, TypeError):
        pass
    return result


def estimate_usage_microusd(usage):
    """Conservative text-input/audio-output upper estimate, or None if uncertain."""
    if type(usage) is not dict:
        return None
    input_tokens = _safe_count(usage.get("input_tokens"), 128_000)
    output_tokens = _safe_count(usage.get("output_tokens"), 32_000)
    details = usage.get("input_token_details")
    image_tokens = details.get("image_tokens", 0) if type(details) is dict else None
    if (input_tokens is None or output_tokens is None or type(details) is not dict or
            details.get("audio_tokens") != 0 or type(details.get("audio_tokens")) is not int or
            image_tokens != 0 or type(image_tokens) is not int):
        return None
    total = usage.get("total_tokens")
    if _safe_count(total, 160_000) is None or total < input_tokens + output_tokens:
        return None
    return input_tokens * 4 + output_tokens * 64


def parse_child_result(raw, expected_mode):
    """Return only bounded, non-secret fields from the untrusted child channel."""
    invalid = {"ok": False, "mode": expected_mode, "phase": "child",
               "error_code": "invalid_child_output", "cleanup": False,
               "inner_cleanup": False, "browser_cleanup": False,
               "usage_estimate_microusd": None}
    if type(raw) is not bytes or not raw or len(raw) > 16_384:
        return invalid
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        return invalid
    if (type(data) is not dict or type(data.get("ok")) is not bool or
            type(data.get("cleanup")) is not bool or data.get("mode") != expected_mode or
            type(data.get("phase")) is not str or not _SAFE_PHASE.fullmatch(data["phase"])):
        return invalid
    code = data.get("error_code")
    if code is not None and (type(code) is not str or not _SAFE_CODE.fullmatch(code)):
        return invalid
    estimate = estimate_usage_microusd(data.get("usage"))
    report = {
        "ok": data["ok"], "mode": expected_mode, "phase": data["phase"],
        "cleanup": data["cleanup"], "usage_estimate_microusd": estimate,
        "inner_cleanup": data.get("inner_cleanup") is True,
        "browser_cleanup": data.get("browser_cleanup") is True,
        "hangup_confirmed_by_child": data.get("provider_hangup_ack") is True,
        "transcript_observed": isinstance(data.get("transcript"), str) and bool(data["transcript"]),
    }
    if estimate is not None:
        details = data["usage"]["input_token_details"]
        report["usage"] = {
            "input_tokens": data["usage"]["input_tokens"],
            "output_tokens": data["usage"]["output_tokens"],
            "input_audio_tokens": details["audio_tokens"],
            "input_image_tokens": details.get("image_tokens", 0),
        }
    if code is not None:
        report["error_code"] = code
    for name, maximum in (("audio_packets", 1_000_000), ("audio_bytes", 100_000_000),
                          ("audio_tracks", 16), ("response_create_count", 2),
                          ("microphone_calls", 16)):
        value = _safe_count(data.get(name), maximum)
        if value is not None:
            report[name] = value
    response_status = data.get("response_status")
    if response_status in ("completed", "cancelled", "failed", "incomplete"):
        report["response_status"] = response_status
    if type(data.get("cancel_acknowledged")) is bool:
        report["cancel_acknowledged"] = data["cancel_acknowledged"]
    timings = data.get("timings")
    if type(timings) is dict:
        allowed = {"total_ms", "setup_ms", "session_created_ms", "response_created_ms",
                   "audio_started_ms", "first_audio_packet_ms", "response_done_ms", "cancel_sent_ms"}
        safe_timings = {}
        for key, value in timings.items():
            checked = _safe_count(value, 120_000) if key in allowed else None
            if checked is not None:
                safe_timings[key] = checked
        report["timings"] = safe_timings
    return report


class SyntheticVoiceProvider(VoiceProvider):
    """One-call server-only provider with a bounded post and server-side hangup."""

    def __init__(self, api_key, transport=None, timer_factory=threading.Timer,
                 clock=time.time, deadline=DEFAULT_DEADLINE):
        super().__init__(api_key, MODEL, transport=transport)
        self._base_transport = self._transport
        self._transport = self._bounded_session_transport
        self._timer_factory = timer_factory
        self._clock = clock
        self._deadline = deadline
        self._state_lock = threading.Lock()
        self._post_done = threading.Event()
        self._post_done.set()
        self._posts = 0
        self._call_id = None
        self._hangup_attempted = False
        self._hangup_done = threading.Event()
        self._hangup_done.set()
        self.hangup_status = None
        self.session_http_status = None
        self.provider_error_code = None
        self.provider_error_param = None
        self.provider_error_hint = None
        self._watchdog = None

    @property
    def session_posts(self):
        with self._state_lock:
            return self._posts

    @property
    def hangup_confirmed(self):
        with self._state_lock:
            return self.hangup_status == 200

    def _session_config(self):
        return {
            "type": "realtime", "model": MODEL,
            "instructions": "Synthetic test only. No personal data. Answer briefly in English, Portuguese and Spanish.",
            "output_modalities": ["audio"], "max_output_tokens": 128,
            "reasoning": {"effort": "minimal"},
            "audio": {"input": {"turn_detection": None}, "output": {"voice": "marin"}},
            "tools": [], "tool_choice": "none", "tracing": None,
        }

    def create_session(self, sdp):
        with self._state_lock:
            if self._posts or self._clock() >= self._deadline:
                raise RuntimeError("Synthetic live session is unavailable.")
            self._posts = 1
            self._post_done.clear()
        try:
            return super().create_session(sdp)
        finally:
            self._post_done.set()

    def _bounded_session_transport(self, request, timeout):
        if request.full_url != ENDPOINT or request.get_method() != "POST":
            raise RuntimeError("Synthetic live session is unavailable.")
        try:
            response = self._base_transport(request, timeout=8)
        except urllib.error.HTTPError as error:
            self.session_http_status = error.code if type(error.code) is int and 100 <= error.code <= 599 else None
            diagnostic = safe_provider_error(error)
            self.provider_error_code = diagnostic["provider_error_code"]
            self.provider_error_param = diagnostic["provider_error_param"]
            self.provider_error_hint = diagnostic["provider_error_hint"]
            raise
        provider = self

        class RegisteredResponse:
            def __enter__(self):
                entered = response.__enter__()
                status = getattr(entered, "status", None)
                provider.session_http_status = status if type(status) is int and 100 <= status <= 599 else None
                try:
                    if status in (200, 201):
                        identifier = call_id_from_location(entered.headers.get("Location"))
                        with provider._state_lock:
                            provider._call_id = identifier
                            delay = max(0, min(60, provider._deadline - provider._clock()))
                            provider._watchdog = provider._timer_factory(delay, provider.hangup_once)
                            provider._watchdog.daemon = True
                            provider._watchdog.start()
                    return entered
                except BaseException as error:
                    response.__exit__(type(error), error, error.__traceback__)
                    raise

            def __exit__(self, *arguments):
                return response.__exit__(*arguments)

        return RegisteredResponse()

    def wait_for_session(self, timeout=25):
        return self._post_done.wait(timeout)

    def hangup_once(self):
        with self._state_lock:
            if self._call_id is None:
                return False
            if self._hangup_attempted:
                already_attempted = True
            else:
                already_attempted = False
                self._hangup_attempted = True
                self._hangup_done.clear()
                identifier = self._call_id
        if already_attempted:
            self._hangup_done.wait(9)
            return self.hangup_confirmed
        request = urllib.request.Request(
            ENDPOINT + "/" + identifier + "/hangup", data=b"", method="POST",
            headers={"Authorization": "Bearer " + self._api_key},
        )
        status = None
        try:
            with self._base_transport(request, timeout=8) as response:
                status = getattr(response, "status", None)
        except urllib.error.HTTPError as error:
            status = error.code
            error.close()
        except Exception:
            pass
        with self._state_lock:
            self.hangup_status = status if type(status) is int and 100 <= status <= 599 else None
            self._hangup_done.set()
        return status == 200

    def close(self):
        self.wait_for_session()
        with self._state_lock:
            timer = self._watchdog
        if timer is not None:
            timer.cancel()
        return self.hangup_once()


class SyntheticTestApplication(Application):
    """A private test-only stop route behind the normal loopback auth boundary."""

    def dispatch(self, method, path, data):
        if method == "POST" and path == "/api/voice/test/end":
            if data:
                raise ValueError("The synthetic hangup action takes no payload.")
            return {"hangup_confirmed": self.voice.hangup_once()}
        return super().dispatch(method, path, data)


def _safe_parser():
    class Parser(argparse.ArgumentParser):
        def error(self, _message):
            raise ValueError("Invalid command line.")
    parser = Parser(description="One explicitly authorized synthetic Realtime voice check", add_help=True)
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--mode", choices=("smoke", "cancel"), required=True)
    parser.add_argument("--node", default=shutil.which("node"))
    return parser


def _node_path(value):
    if not value:
        raise ValueError("A Node.js executable is required.")
    selected = shutil.which(value) if os.path.sep not in value else value
    if not selected:
        raise ValueError("A Node.js executable is required.")
    path = Path(selected).resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError("A Node.js executable is required.")
    return path


def run_live_check(config, mode, node_path, *, child_runner=subprocess.run,
                   budget_factory=TestBudget, provider_factory=SyntheticVoiceProvider):
    """Execute one authorized attempt; no automatic retry or raw provider output."""
    validate_live_config(config)
    if mode not in ("smoke", "cancel"):
        raise ValueError("Invalid synthetic voice test mode.")
    node = _node_path(str(node_path) if node_path is not None else None)
    if not CHILD_SCRIPT.is_file():
        raise ValueError("Synthetic browser child is unavailable.")
    path = config.data_dir / "development" / "voice-budget.sqlite3"
    with budget_factory(path, limit_microusd=TOTAL_LIMIT_MICROUSD, deadline=DEFAULT_DEADLINE) as budget:
        reservation = budget.reserve(RESERVE_MICROUSD, "voice_" + mode,
                                     max_reservations=MAX_ATTEMPTS, require_prior_completed=True)
        provider = None
        app = server = worker = scratch = None
        child = {"ok": False, "mode": mode, "phase": "parent", "error_code": "execution_failed",
                 "cleanup": False, "usage_estimate_microusd": None}
        try:
            provider = provider_factory(config.api_key)
            scratch = tempfile.TemporaryDirectory(prefix="wanda-live-voice-")
            temporary = replace(config, data_dir=Path(scratch.name), home_mode="mock",
                                home_url="", home_token="", home_entities=(),
                                home_allow_insecure_http=False)
            app = SyntheticTestApplication(temporary, voice=provider)
            server = LocalServer(app, port=0)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            input_line = json.dumps({"base": f"http://127.0.0.1:{server.server_address[1]}",
                                     "token": app.token, "mode": mode}).encode("utf-8") + b"\n"
            try:
                completed = child_runner(
                    [str(node), str(CHILD_SCRIPT)], input=input_line,
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    timeout=75, cwd=ROOT, env=child_environment(), check=False,
                )
                child = parse_child_result(completed.stdout, mode)
                if completed.returncode != 0:
                    child["ok"] = False
                    child.setdefault("error_code", "child_exit_failed")
            except subprocess.TimeoutExpired:
                child = {"ok": False, "mode": mode, "phase": "child",
                         "error_code": "child_timeout", "cleanup": False,
                         "usage_estimate_microusd": None}
        except Exception:
            # Never reflect request bodies, credentials, SDP, call IDs or raw
            # exception strings into logs or the CLI result.
            child = {"ok": False, "mode": mode, "phase": "parent",
                     "error_code": "execution_failed", "cleanup": False,
                     "usage_estimate_microusd": None}
        finally:
            cleanup_ok = True
            try:
                hangup_confirmed = provider.close() if provider is not None else False
            except Exception:
                hangup_confirmed = False
            if server is not None:
                try:
                    server.shutdown()
                except Exception:
                    cleanup_ok = False
                try:
                    server.server_close()
                except Exception:
                    cleanup_ok = False
            if worker is not None:
                worker.join(timeout=3)
                if worker.is_alive():
                    cleanup_ok = False
            if app is not None:
                try:
                    app.close()
                except Exception:
                    cleanup_ok = False
            if scratch is not None:
                try:
                    scratch.cleanup()
                except Exception:
                    cleanup_ok = False
            usage_estimate = child.get("usage_estimate_microusd")
            response_verified = (
                (mode == "smoke" and child.get("response_status") == "completed" and
                 child.get("audio_packets", 0) > 0 and child.get("audio_bytes", 0) > 0 and
                 child.get("transcript_observed") is True) or
                (mode == "cancel" and child.get("response_status") == "cancelled" and
                 child.get("cancel_acknowledged") is True)
            )
            complete = (child.get("ok") is True and child.get("cleanup") is True and
                        child.get("inner_cleanup") is True and
                        child.get("browser_cleanup") is True and
                        child.get("hangup_confirmed_by_child") is True and
                        response_verified and
                        provider is not None and provider.session_posts == 1 and
                        provider.session_http_status in (200, 201) and
                        hangup_confirmed and cleanup_ok and usage_estimate is not None and
                        child.get("microphone_calls") == 0 and
                        child.get("response_create_count") == 1)
            status = "completed" if complete else "unknown"
            budget.record_result(reservation, estimated_microusd=usage_estimate, status=status)
        return {**child, "ok": complete, "hangup_confirmed": hangup_confirmed,
                "session_http_status": provider.session_http_status if provider is not None else None,
                "hangup_http_status": provider.hangup_status if provider is not None else None,
                "provider_error_code": provider.provider_error_code if provider is not None else None,
                "provider_error_param": provider.provider_error_param if provider is not None else None,
                "provider_error_hint": provider.provider_error_hint if provider is not None else None,
                "session_posts": provider.session_posts if provider is not None else 0,
                "budget": budget.snapshot()}


def main(argv=None):
    try:
        args = _safe_parser().parse_args(argv)
        if not args.allow_paid:
            raise PermissionError("Paid test requires explicit opt-in.")
        node = _node_path(args.node)
        config = Config.load()
        result = run_live_check(config, args.mode, node)
        print(json.dumps(result, separators=(",", ":"), allow_nan=False))
        return 0 if result["ok"] else 1
    except PermissionError:
        print('{"ok":false,"error_code":"authorization_or_budget_denied"}')
        return 2
    except Exception:
        print('{"ok":false,"error_code":"preflight_or_execution_failed"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
