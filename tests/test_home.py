"""Synthetic home-control tests. No real Home Assistant or devices are contacted."""

from concurrent.futures import ThreadPoolExecutor
import threading
import unittest

from wanda.home import HomeAssistantAdapter, HomeService, MockHomeAdapter, _NoRedirect


class MockHomeTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000.0
        self.service = HomeService(MockHomeAdapter(), clock=lambda: self.now)
        self.owner = "resident-a"
        self.entity = "light.demo_lamp"

    def test_denied_by_default_and_owner_isolation(self):
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_on", "a")["status"], "denied")
        grant = self.service.grant(self.owner, self.entity, "turn_on", confirmation=False)
        self.assertEqual(self.service.act("resident-b", self.entity, "turn_on", "b")["status"], "denied")
        self.assertEqual(self.service.snapshot("resident-b")["grants"], [])
        self.assertFalse(self.service.revoke("resident-b", grant["id"]))
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_on", "c")["status"], "verified")
        self.assertEqual(self.service.snapshot(self.owner)["devices"][0]["state"], "on")

    def test_confirmation_is_bound_to_action_owner_and_request(self):
        self.service.grant(self.owner, self.entity, "turn_on")
        first = self.service.act(self.owner, self.entity, "turn_on", "req-1")
        self.assertEqual(first["status"], "confirmation_required")
        nonce = first["confirmation_id"]
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_on", "req-1")["confirmation_id"], nonce)
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_off", "req-1", nonce)["status"], "denied")
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_on", "req-2", nonce)["status"], "denied")
        self.assertEqual(self.service.act("resident-b", self.entity, "turn_on", "req-1", nonce)["status"], "denied")
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_on", "req-1", "wrong")["status"], "denied")
        self.assertEqual(self.service.snapshot(self.owner)["devices"][0]["state"], "off")
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_on", "req-1", nonce)["status"], "verified")
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_on", "req-1", nonce)["status"], "verified")
        self.assertEqual(len([item for item in self.service.snapshot(self.owner)["audit"] if item["status"] == "verified"]), 1)

    def test_revoke_and_expiry_block_pending_confirmation(self):
        grant = self.service.grant(self.owner, self.entity, "turn_on")
        nonce = self.service.act(self.owner, self.entity, "turn_on", "req-1")["confirmation_id"]
        self.assertTrue(self.service.revoke(self.owner, grant["id"]))
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_on", "req-1", nonce)["status"], "denied")
        self.service.grant(self.owner, self.entity, "turn_on", expires_at=self.now + 2)
        nonce = self.service.act(self.owner, self.entity, "turn_on", "req-2")["confirmation_id"]
        self.now += 3
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_on", "req-2", nonce)["status"], "denied")
        self.assertEqual(self.service.snapshot(self.owner)["grants"], [])

    def test_confirmation_timeout_requires_new_request(self):
        self.service.grant(self.owner, self.entity, "turn_on")
        nonce = self.service.act(self.owner, self.entity, "turn_on", "req-1")["confirmation_id"]
        self.now += 61
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_on", "req-1", nonce)["status"], "denied")
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_on", "req-2")["status"], "confirmation_required")

    def test_regrant_does_not_validate_old_confirmation(self):
        original = self.service.grant(self.owner, self.entity, "turn_on")
        nonce = self.service.act(self.owner, self.entity, "turn_on", "req-1")["confirmation_id"]
        self.service.revoke(self.owner, original["id"])
        self.service.grant(self.owner, self.entity, "turn_on")
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_on", "req-1", nonce)["status"], "denied")
        self.assertEqual(self.service.snapshot(self.owner)["devices"][0]["state"], "off")

    def test_outage_and_recovery_never_claim_false_completion(self):
        self.service.grant(self.owner, self.entity, "turn_on", confirmation=False)
        self.service.set_outage(True)
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_on", "req-1")["status"], "unavailable")
        self.assertEqual(self.service.snapshot(self.owner)["devices"][0]["state"], "unavailable")
        self.service.set_outage(False)
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_on", "req-1")["status"], "unavailable")
        self.assertEqual(self.service.act(self.owner, self.entity, "turn_on", "req-2")["status"], "verified")

    def test_invalid_scope_is_rejected(self):
        for entity in ("switch.pump", "light.bad/name", "light.X"):
            with self.assertRaises(ValueError):
                self.service.grant(self.owner, entity, "turn_on")
        with self.assertRaises(ValueError):
            self.service.grant(self.owner, self.entity, "toggle")
        with self.assertRaises(ValueError):
            self.service.grant(self.owner, self.entity, "turn_on", expires_at=self.now)
        with self.assertRaises(ValueError):
            self.service.grant(self.owner, self.entity, "turn_on", expires_at=float("nan"))
        with self.assertRaises(ValueError):
            self.service.grant(self.owner, self.entity, "turn_on", confirmation="false")
        self.service.grant(self.owner, self.entity, "turn_on", confirmation=False)
        with self.assertRaises(ValueError):
            self.service.grant(self.owner, self.entity, "turn_on", confirmation=True)


class CountingAdapter(MockHomeAdapter):
    def __init__(self):
        super().__init__()
        self.calls = 0
        self.call_lock = threading.Lock()

    def perform(self, entity_id, action):
        with self.call_lock:
            self.calls += 1
        return super().perform(entity_id, action)


class IdempotencyTests(unittest.TestCase):
    def test_concurrent_same_request_only_acts_once(self):
        adapter = CountingAdapter()
        service = HomeService(adapter)
        service.grant("owner", "light.demo_lamp", "turn_on", confirmation=False)
        with ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(lambda _: service.act("owner", "light.demo_lamp", "turn_on", "same"), range(100)))
        self.assertTrue(all(result["status"] == "verified" for result in results))
        self.assertEqual(adapter.calls, 1)
        self.assertEqual(service.act("owner", "light.demo_lamp", "turn_off", "same")["status"], "denied")


class HomeAssistantTests(unittest.TestCase):
    def test_exact_rest_calls_and_state_verification(self):
        calls = []

        def transport(method, url, headers, payload):
            calls.append((method, url, headers, payload))
            if method == "POST":
                return 200, []
            return 200, {"entity_id": "light.test", "state": "on", "attributes": {"friendly_name": "Test light"}}

        adapter = HomeAssistantAdapter("http://localhost:8123", "synthetic-token", ["light.test"], transport=transport)
        service = HomeService(adapter)
        service.grant("owner", "light.test", "turn_on", confirmation=False)
        result = service.act("owner", "light.test", "turn_on", "req")
        self.assertEqual(result["status"], "verified")
        self.assertEqual([call[0] for call in calls], ["POST", "GET"])
        self.assertEqual(calls[0][1], "http://localhost:8123/api/services/light/turn_on")
        self.assertEqual(calls[0][3], {"entity_id": "light.test"})
        self.assertEqual(calls[1][1], "http://localhost:8123/api/states/light.test")
        self.assertEqual(calls[0][2]["Authorization"], "Bearer synthetic-token")

    def test_unverified_on_state_mismatch_and_no_retry(self):
        calls = []

        def transport(method, url, headers, payload):
            calls.append(method)
            if method == "POST":
                return 200, []
            return 200, {"entity_id": "light.test", "state": "off"}

        service = HomeService(HomeAssistantAdapter("http://localhost:8123", "synthetic-token", ["light.test"], transport=transport))
        service.grant("owner", "light.test", "turn_on", confirmation=False)
        self.assertEqual(service.act("owner", "light.test", "turn_on", "req")["status"], "unverified")
        self.assertEqual(service.act("owner", "light.test", "turn_on", "req")["status"], "unverified")
        self.assertEqual(calls, ["POST", "GET"])

    def test_instance_outage_does_not_repeat_timeout_for_every_light(self):
        calls = []

        def transport(method, url, headers, payload):
            calls.append(url)
            raise TimeoutError("synthetic instance outage")

        adapter = HomeAssistantAdapter("http://localhost:8123", "synthetic-token",
                                       ["light.first", "light.second"], transport=transport)
        devices = adapter.list_devices()
        self.assertEqual(len(calls), 1)
        self.assertEqual([device["state"] for device in devices], ["unavailable", "unavailable"])

    def test_http_error_and_exception_are_redacted(self):
        secret = "synthetic-token"
        for transport in (
            lambda *_: (401, {"error": "token=" + secret}),
            lambda *_: (_ for _ in ()).throw(RuntimeError("token=" + secret)),
        ):
            adapter = HomeAssistantAdapter("http://localhost:8123", secret, ["light.test"], transport=transport)
            result = adapter.perform("light.test", "turn_on")
            self.assertEqual(result["status"], "unverified")
            self.assertNotIn(secret, result["message"])

    def test_allowlist_transport_and_url_validation(self):
        calls = []
        adapter = HomeAssistantAdapter("https://example.invalid", "synthetic", ["light.test"],
                                       transport=lambda *args: calls.append(args))
        self.assertEqual(adapter.perform("light.other", "turn_on")["status"], "denied")
        self.assertEqual(calls, [])
        for url in ("http://example.invalid", "https://name:pass@example.invalid", "https://example.invalid/path",
                    "https://example.invalid:bad", "https://example.invalid:0"):
            with self.assertRaises(ValueError):
                HomeAssistantAdapter(url, "synthetic", ["light.test"], transport=lambda *_: None)
        with self.assertRaises(ValueError):
            HomeAssistantAdapter("https://example.invalid", "synthetic", ["switch.test"])
        with self.assertRaises(ValueError):
            HomeAssistantAdapter("http://example.invalid", "synthetic", ["light.test"], allow_insecure_http="false")
        self.assertEqual(HomeAssistantAdapter("http://example.invalid", "synthetic", ["light.test"],
                                              allow_insecure_http=True, transport=lambda *_: None).mode, "homeassistant")

    def test_redirect_handler_rejects_redirect_request(self):
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 302, "moved", {}, "https://other.invalid"))


if __name__ == "__main__":
    unittest.main()
