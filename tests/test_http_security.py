"""Local HTTP boundary tests with synthetic state and no external connections."""

import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from wanda.config import Config


class FakeMemory:
    def __init__(self):
        self.enabled = False
        self.calls = []

    def is_enabled(self, owner):
        self.calls.append(("is_enabled", owner))
        return self.enabled

    def set_enabled(self, owner, enabled):
        self.calls.append(("set_enabled", owner, enabled))
        self.enabled = enabled

    def list_memories(self, owner):
        self.calls.append(("list_memories", owner))
        return []

    def close(self):
        pass


class BombVoice:
    def __init__(self):
        self.calls = 0

    def create_session(self, sdp):
        self.calls += 1
        raise AssertionError("Disabled voice must not reach a provider")


class LocalHttpSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from wanda.server import Application, LocalServer
        cls.Application = Application
        cls.LocalServer = LocalServer

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wanda-http-test-")
        self.memory = FakeMemory()
        self.voice = BombVoice()
        config = Config(data_dir=Path(self.temp.name), api_key="synthetic-api-secret",
                        home_token="synthetic-home-secret", voice_enabled=False)
        self.app = self.Application(config, memory=self.memory, voice=self.voice)
        self.server = self.LocalServer(self.app, port=0)
        self.port = self.server.server_address[1]
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=2)
        self.app.close()
        self.temp.cleanup()

    def request(self, method, path, data=None, *, auth=True, headers=None, raw=False):
        body = data if raw else (None if data is None else json.dumps(data).encode("utf-8"))
        request_headers = {"Host": f"127.0.0.1:{self.port}"}
        if auth:
            request_headers["Authorization"] = "Bearer " + self.app.token
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        if headers:
            request_headers.update(headers)
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            payload = response.read()
            try:
                decoded = json.loads(payload)
            except (ValueError, UnicodeError):
                decoded = payload
            return response.status, decoded, payload
        finally:
            connection.close()

    def test_unauthorized_memory_reads_and_writes(self):
        status, data, _ = self.request("GET", "/api/memory", auth=False)
        self.assertEqual((status, data["code"]), (401, "unauthorized"))
        status, data, _ = self.request("POST", "/api/memory/consent", {"enabled": True}, auth=False)
        self.assertEqual((status, data["code"]), (401, "unauthorized"))
        self.assertEqual(self.memory.calls, [])

    def test_cross_origin_host_and_fetch_site_are_rejected(self):
        for headers, code in (
            ({"Origin": "https://untrusted.invalid"}, "invalid_origin"),
            ({"Host": "untrusted.invalid"}, "invalid_host"),
            ({"Sec-Fetch-Site": "cross-site"}, "cross_site"),
        ):
            status, data, _ = self.request("POST", "/api/memory/consent", {"enabled": True}, headers=headers)
            self.assertEqual((status, data["code"]), (403, code))
        self.assertFalse(self.memory.enabled)

    def test_wrong_content_type_oversize_and_malformed_json(self):
        status, data, _ = self.request("POST", "/api/memory/consent", b'{"enabled":true}', raw=True,
                                       headers={"Content-Type": "text/plain"})
        self.assertEqual((status, data["code"]), (415, "json_required"))
        status, data, _ = self.request("POST", "/api/memory/consent", b"x" * 131073, raw=True)
        self.assertEqual((status, data["code"]), (413, "body_too_large"))
        for body in (b"{", b"[]", b'{"enabled":NaN}'):
            status, data, _ = self.request("POST", "/api/memory/consent", body, raw=True)
            self.assertEqual((status, data["code"]), (400, "invalid_request"))
        self.assertFalse(self.memory.enabled)

    def test_boolean_validation_and_owner_spoof_have_no_authority(self):
        status, data, _ = self.request("POST", "/api/memory/consent", {"enabled": 1, "owner": "other"})
        self.assertEqual((status, data["code"]), (400, "invalid_request"))
        status, data, _ = self.request("POST", "/api/memory/consent", {"enabled": True, "owner": "other"})
        self.assertEqual((status, data["enabled"]), (200, True))
        self.assertIn(("set_enabled", "local-owner", True), self.memory.calls)
        self.assertFalse(any(call[1] == "other" for call in self.memory.calls))

    def test_status_and_errors_do_not_disclose_credentials(self):
        status, _, payload = self.request("GET", "/api/status")
        self.assertEqual(status, 200)
        self.assertNotIn(b"synthetic-api-secret", payload)
        self.assertNotIn(b"synthetic-home-secret", payload)
        status, data, payload = self.request("POST", "/api/memory/consent",
                                               b'{"enabled":"synthetic-api-secret"}', raw=True)
        self.assertEqual((status, data["code"]), (400, "invalid_request"))
        self.assertNotIn(b"synthetic-api-secret", payload)

    def test_static_traversal_and_csrf_attempts(self):
        for path in ("/../wanda/config.py", "/%2e%2e/wanda/config.py", "/app.js/../config.py"):
            status, data, _ = self.request("GET", path, auth=False)
            self.assertEqual((status, data["code"]), (404, "not_found"))
        status, data, _ = self.request("OPTIONS", "/api/memory/consent", auth=False,
                                       headers={"Origin": "https://untrusted.invalid"})
        self.assertEqual((status, data["code"]), (403, "invalid_origin"))
        status, data, _ = self.request("POST", "/api/memory/consent", {"enabled": True}, auth=False,
                                       headers={"Origin": f"http://127.0.0.1:{self.port}"})
        self.assertEqual((status, data["code"]), (401, "unauthorized"))

    def test_disabled_voice_fails_before_provider_call(self):
        status, data, _ = self.request("POST", "/api/voice/session", {"sdp": "synthetic", "audio_consent": True})
        self.assertEqual((status, data["code"]), (503, "voice_not_configured"))
        self.assertEqual(self.voice.calls, 0)

    def test_home_grant_scope_and_duplicate_confirmation(self):
        status, data, _ = self.request("POST", "/api/home/action",
                                       {"entity_id": "light.demo_lamp", "action": "turn_on", "request_id": "one"})
        self.assertEqual((status, data["status"]), (200, "denied"))
        for payload in (
            {"entity_id": "switch.bad", "action": "turn_on", "confirmation": True},
            {"entity_id": "light.demo_lamp", "action": "toggle", "confirmation": True},
            {"entity_id": "light.demo_lamp", "action": "turn_on", "confirmation": "false"},
            {"entity_id": "light.demo_lamp", "action": "turn_on", "confirmation": True, "expires_at": False},
        ):
            status, data, _ = self.request("POST", "/api/home/grants", payload)
            self.assertEqual((status, data["code"]), (400, "invalid_request"))
        grant = {"entity_id": "light.demo_lamp", "action": "turn_on", "confirmation": True}
        status, data, _ = self.request("POST", "/api/home/grants", grant)
        self.assertEqual(status, 200)
        status, data, _ = self.request("POST", "/api/home/grants", grant)
        self.assertEqual((status, data["code"]), (400, "invalid_request"))
        action = {"entity_id": "light.demo_lamp", "action": "turn_on", "request_id": "two"}
        status, data, _ = self.request("POST", "/api/home/action", action)
        self.assertEqual((status, data["status"]), (200, "confirmation_required"))
        nonce = data["confirmation_id"]
        status, data, _ = self.request("POST", "/api/home/action", dict(action, confirmation_id="wrong"))
        self.assertEqual((status, data["status"]), (200, "denied"))
        status, data, _ = self.request("POST", "/api/home/action", dict(action, confirmation_id=nonce))
        self.assertEqual((status, data["status"]), (200, "verified"))
        status, data, _ = self.request("POST", "/api/home/action", dict(action, confirmation_id=nonce))
        self.assertEqual((status, data["status"]), (200, "verified"))
        status, data, _ = self.request("GET", "/api/home")
        self.assertEqual(status, 200)
        self.assertEqual(len([item for item in data["audit"] if item["status"] == "verified"]), 1)


if __name__ == "__main__":
    unittest.main()
