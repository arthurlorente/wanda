"""Offline checks for the opt-in synthetic paid voice harness; no provider calls."""

from io import BytesIO, StringIO
from http.client import HTTPConnection
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error

from scripts import live_voice_check as live
from scripts.live_test_budget import TestBudget
from wanda.config import Config


class _Response:
    def __init__(self, status, location=None, body=b"v=0\r\n"):
        self.status = status
        self.headers = {"Location": location} if location else {}
        self.body = BytesIO(body)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def read(self, size):
        return self.body.read(size)


class _Timer:
    def __init__(self, delay, callback):
        self.delay, self.callback = delay, callback
        self.daemon = False

    def start(self):
        pass

    def cancel(self):
        pass


def usage(image_tokens=None):
    details = {"audio_tokens": 0, "text_tokens": 3}
    if image_tokens is not None:
        details["image_tokens"] = image_tokens
    return {"total_tokens": 5, "input_tokens": 3, "output_tokens": 2,
            "input_token_details": details}


class LiveVoiceCheckTests(unittest.TestCase):
    @staticmethod
    def fixed_budget(path, **kwargs):
        return TestBudget(path, clock=lambda: live.DEFAULT_DEADLINE - 100, **kwargs)

    def test_call_location_exact_provider_origin_and_path(self):
        valid = "/v1/realtime/calls/rtc_ABC-12_xyz"
        self.assertEqual(live.call_id_from_location(valid), "rtc_ABC-12_xyz")
        self.assertEqual(live.call_id_from_location("https://api.openai.com" + valid), "rtc_ABC-12_xyz")
        for bad in ("https://attacker.example" + valid, "http://api.openai.com" + valid,
                    "https://api.openai.com.evil" + valid, valid + "?next=evil",
                    valid + "/hangup", "/v1/realtime/calls/../../evil",
                    "https://api.openai.com:443" + valid, "", "rtc_ABC"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                live.call_id_from_location(bad)

    def test_provider_one_post_fixed_session_and_hangup_authorization(self):
        calls = []

        def transport(request, timeout):
            calls.append((request, timeout))
            if len(calls) == 1:
                return _Response(201, "/v1/realtime/calls/rtc_safe123")
            return _Response(200)

        provider = live.SyntheticVoiceProvider("synthetic-key", transport=transport,
                                                timer_factory=_Timer, clock=lambda: live.DEFAULT_DEADLINE - 100)
        self.assertEqual(provider.create_session("v=0\r\n"), "v=0\r\n")
        with self.assertRaises(RuntimeError):
            provider.create_session("v=0\r\n")
        app = live.SyntheticTestApplication.__new__(live.SyntheticTestApplication)
        app.voice = provider
        self.assertEqual(app.dispatch("POST", "/api/voice/test/end", {}), {"hangup_confirmed": True})
        self.assertTrue(provider.close())
        self.assertEqual((provider.session_posts, provider.session_http_status, provider.hangup_status), (1, 201, 200))
        self.assertEqual(len(calls), 2)
        session, hangup = (item[0] for item in calls)
        self.assertEqual([item[1] for item in calls], [8, 8])
        self.assertEqual(session.get_method(), "POST")
        self.assertEqual(hangup.full_url, live.ENDPOINT + "/rtc_safe123/hangup")
        self.assertEqual(hangup.get_method(), "POST")
        self.assertEqual(hangup.get_header("Authorization"), "Bearer synthetic-key")
        body = session.data.decode("utf-8")
        self.assertIn('"model": "gpt-realtime-2.1"', body)
        self.assertIn('"max_output_tokens": 128', body)
        self.assertIn('"turn_detection": null', body)
        self.assertIn('"tool_choice": "none"', body)
        with self.assertRaises(ValueError):
            app.dispatch("POST", "/api/voice/test/end", {"extra": True})

    def test_missing_location_blocks_sdp_and_hangup(self):
        calls = []

        def transport(request, timeout):
            calls.append(request)
            return _Response(201, body=b"v=0\r\n")

        provider = live.SyntheticVoiceProvider("synthetic-key", transport=transport,
                                                timer_factory=_Timer, clock=lambda: live.DEFAULT_DEADLINE - 100)
        with self.assertRaises(ValueError):
            provider.create_session("v=0\r\n")
        self.assertFalse(provider.close())
        self.assertEqual(provider.session_http_status, 201)
        self.assertEqual(len(calls), 1)

    def test_http_error_status_is_sanitized_and_no_retry(self):
        calls = []

        def transport(request, timeout):
            calls.append(request)
            body = json.dumps({"error": {
                "code": "invalid_request_error", "param": "sdp",
                "message": "Failed to parse SDP: synthetic-key is private",
            }}).encode("utf-8")
            raise urllib.error.HTTPError(request.full_url, 400, "sensitive-key-in-reason", {}, BytesIO(body))

        provider = live.SyntheticVoiceProvider("synthetic-key", transport=transport,
                                                timer_factory=_Timer, clock=lambda: live.DEFAULT_DEADLINE - 100)
        with self.assertRaises(RuntimeError) as raised:
            provider.create_session("v=0\r\n")
        self.assertNotIn("sensitive", str(raised.exception))
        self.assertEqual(provider.session_http_status, 400)
        self.assertEqual((provider.provider_error_code, provider.provider_error_param,
                          provider.provider_error_hint),
                         ("invalid_request_error", "sdp", "sdp_parse_failed"))
        self.assertNotIn("synthetic-key", json.dumps({
            "code": provider.provider_error_code,
            "param": provider.provider_error_param,
            "hint": provider.provider_error_hint,
        }))
        self.assertFalse(provider.close())
        self.assertEqual(len(calls), 1)

    def test_hostile_provider_error_values_are_never_reflected(self):
        private = "sk-this-must-never-appear"
        for content in (
            {"error": {"code": private, "param": private, "message": private}},
            {"error": {"code": [private], "param": {"secret": private}, "message": 1}},
        ):
            error = urllib.error.HTTPError(live.ENDPOINT, 400, private, {},
                                           BytesIO(json.dumps(content).encode("utf-8")))
            try:
                self.assertEqual(live.safe_provider_error(error), {
                    "provider_error_code": None, "provider_error_param": None,
                    "provider_error_hint": None,
                })
            finally:
                error.close()
        oversized = urllib.error.HTTPError(live.ENDPOINT, 400, private, {}, BytesIO(b"x" * 10_241))
        try:
            self.assertEqual(live.safe_provider_error(oversized)["provider_error_code"], None)
        finally:
            oversized.close()

    def test_usage_bounds_and_optional_image_default(self):
        self.assertEqual(live.estimate_usage_microusd(usage()), 140)
        self.assertEqual(live.estimate_usage_microusd(usage(0)), 140)
        for bad in (True, 1, "0", -1):
            with self.subTest(image=bad):
                self.assertIsNone(live.estimate_usage_microusd(usage(bad)))
        for alteration in (
            {"input_tokens": True}, {"output_tokens": 32_001}, {"input_tokens": 128_001},
            {"total_tokens": 4}, {"input_token_details": {"audio_tokens": 1}},
            {"input_token_details": {"audio_tokens": True}},
            {"input_token_details": {}},
        ):
            candidate = usage()
            candidate.update(alteration)
            with self.subTest(alteration=alteration):
                self.assertIsNone(live.estimate_usage_microusd(candidate))

    def test_child_result_only_safe_fields_and_requires_both_cleanups(self):
        data = {"ok": True, "mode": "smoke", "phase": "response", "cleanup": True,
                "inner_cleanup": True, "browser_cleanup": True, "provider_hangup_ack": True,
                "usage": usage(), "transcript": "sensitive synthetic words",
                "call_id": "rtc_secret", "sdp": "secret", "response_create_count": 1,
                "microphone_calls": 0, "timings": {"total_ms": 42, "private": "secret"}}
        report = live.parse_child_result(json.dumps(data).encode(), "smoke")
        self.assertEqual(report["usage"], {"input_tokens": 3, "output_tokens": 2,
                                           "input_audio_tokens": 0, "input_image_tokens": 0})
        self.assertTrue(report["transcript_observed"])
        self.assertTrue(report["inner_cleanup"])
        self.assertTrue(report["browser_cleanup"])
        self.assertTrue(report["hangup_confirmed_by_child"])
        self.assertNotIn("secret", json.dumps(report))
        self.assertEqual(report["timings"], {"total_ms": 42})
        data.pop("inner_cleanup")
        self.assertFalse(live.parse_child_result(json.dumps(data).encode(), "smoke")["inner_cleanup"])
        self.assertEqual(live.parse_child_result(b"not-json", "smoke")["error_code"], "invalid_child_output")

    def test_child_environment_excludes_keys_and_debug_controls(self):
        env = live.child_environment({"PATH": "/usr/bin", "HOME": "/tmp/synthetic",
                                      "OPENAI_API_KEY": "secret", "HOME_ASSISTANT_TOKEN": "secret",
                                      "NODE_OPTIONS": "--require attacker", "DEBUG": "secret",
                                      "WANDA_TEST_BROWSER": "chromium"})
        self.assertEqual(env, {"PATH": "/usr/bin", "HOME": "/tmp/synthetic",
                               "WANDA_TEST_BROWSER": "chromium"})

    def test_cli_no_optin_does_not_load_private_config(self):
        output = StringIO()
        with patch.object(live.Config, "load", side_effect=AssertionError("should not load")), patch("sys.stdout", output):
            result = live.main(["--mode", "smoke"])
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(output.getvalue()), {"ok": False, "error_code": "authorization_or_budget_denied"})

    def test_uncertain_attempt_charges_budget_and_blocks_second_attempt(self):
        class FakeApp:
            token = "synthetic-local-capability"

            def close(self):
                pass

        class FakeServer:
            server_address = ("127.0.0.1", 8765)

            def serve_forever(self):
                pass

            def shutdown(self):
                pass

            def server_close(self):
                pass

        class FakeProvider:
            session_posts = 0
            session_http_status = None
            hangup_status = None
            provider_error_code = None
            provider_error_param = None
            provider_error_hint = None

            def close(self):
                return False

        captured = []

        def child_runner(command, **kwargs):
            captured.append((command, kwargs))
            return SimpleNamespace(returncode=1, stdout=b'{"ok":false,"mode":"smoke","phase":"setup","cleanup":true}')

        with tempfile.TemporaryDirectory(prefix="wanda-live-parent-test-") as directory:
            config = Config(data_dir=Path(directory), voice_enabled=True,
                            api_key="synthetic-key", voice_model=live.MODEL)
            with patch.object(live, "SyntheticTestApplication", return_value=FakeApp()), \
                    patch.object(live, "LocalServer", return_value=FakeServer()):
                result = live.run_live_check(config, "smoke", sys.executable,
                                             child_runner=child_runner,
                                             budget_factory=self.fixed_budget,
                                             provider_factory=lambda _: FakeProvider())
                self.assertFalse(result["ok"])
                self.assertEqual(result["budget"]["charged_microusd"], 3_000_000)
                self.assertEqual(result["budget"]["reservations"], 1)
                self.assertIsNone(result["session_http_status"])
                self.assertIsNone(result["hangup_http_status"])
                with self.assertRaises(PermissionError):
                    live.run_live_check(config, "cancel", sys.executable,
                                        child_runner=child_runner,
                                        budget_factory=self.fixed_budget,
                                        provider_factory=lambda _: FakeProvider())
        self.assertEqual(len(captured), 1)
        args = captured[0][1]
        self.assertNotIn("synthetic-key", args["input"].decode("utf-8"))
        self.assertEqual(json.loads(args["input"]), {"base": "http://127.0.0.1:8765",
                                                     "token": "synthetic-local-capability", "mode": "smoke"})

    def test_offline_loopback_session_authenticated_end_and_lifecycle(self):
        """Real local HTTP boundary with an entirely fake provider transport."""
        calls = []

        def transport(request, timeout):
            calls.append((request.full_url, timeout))
            if len(calls) == 1:
                return _Response(201, "/v1/realtime/calls/rtc_offline")
            return _Response(200)

        def request(base, path, token=None, origin=None, body=None):
            port = int(base.rsplit(":", 1)[1])
            connection = HTTPConnection("127.0.0.1", port, timeout=5)
            headers = {"Content-Type": "application/json"}
            if token is not None:
                headers["Authorization"] = "Bearer " + token
            if origin is not None:
                headers["Origin"] = origin
            connection.request("POST", path, body=json.dumps(body or {}), headers=headers)
            response = connection.getresponse()
            status, data = response.status, response.read()
            connection.close()
            return status, json.loads(data)

        def child_runner(command, **kwargs):
            details = json.loads(kwargs["input"])
            base, token = details["base"], details["token"]
            self.assertEqual(request(base, "/api/voice/test/end")[0], 401)
            self.assertEqual(request(base, "/api/voice/test/end", token, "http://foreign.invalid")[0], 403)
            status, answer = request(base, "/api/voice/session", token, body={
                "sdp": "v=0\r\n", "audio_consent": True,
            })
            self.assertEqual(status, 200)
            self.assertEqual(answer, {"sdp": "v=0\r\n"})
            status, ended = request(base, "/api/voice/test/end", token)
            self.assertEqual((status, ended), (200, {"hangup_confirmed": True}))
            return SimpleNamespace(returncode=0, stdout=json.dumps({
                "ok": True, "mode": "smoke", "phase": "response", "cleanup": True,
                "inner_cleanup": True, "browser_cleanup": True, "provider_hangup_ack": True,
                "usage": usage(), "response_status": "completed", "audio_packets": 1,
                "audio_bytes": 100, "transcript": "synthetic hello", "response_create_count": 1,
                "microphone_calls": 0,
            }).encode("utf-8"))

        with tempfile.TemporaryDirectory(prefix="wanda-live-http-test-") as directory:
            config = Config(data_dir=Path(directory), voice_enabled=True,
                            api_key="synthetic-key", voice_model=live.MODEL)
            result = live.run_live_check(config, "smoke", sys.executable,
                                         child_runner=child_runner,
                                         budget_factory=self.fixed_budget,
                                         provider_factory=lambda key: live.SyntheticVoiceProvider(
                                             key, transport=transport, timer_factory=_Timer,
                                             clock=lambda: live.DEFAULT_DEADLINE - 100))
        self.assertTrue(result["ok"], {key: result.get(key) for key in (
            "phase", "error_code", "cleanup", "inner_cleanup", "browser_cleanup",
            "hangup_confirmed", "session_http_status", "hangup_http_status", "session_posts")})
        self.assertEqual((result["session_http_status"], result["hangup_http_status"]), (201, 200))
        self.assertEqual(result["budget"]["charged_microusd"], 3_000_000)
        self.assertEqual(result["session_posts"], 1)
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
