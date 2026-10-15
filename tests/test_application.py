"""Integrated local workflows; all users, devices and credentials are synthetic."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock

from wanda.config import Config
from wanda.server import Application, ApiError, OWNER


class AppTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config = Config(data_dir=Path(self.directory.name))
        self.app = Application(self.config)
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.app.close)

    def call(self, method, path, data=None):
        return self.app.dispatch(method, path, data or {})

    def test_local_demo_memory_restart_delete_and_disable(self):
        self.assertFalse(self.call("GET", "/api/status")["memory_enabled"])
        reply = self.call("POST", "/api/chat", {"text": "My favorite color is green."})
        self.assertEqual(reply["memory_saved"], [])
        self.call("POST", "/api/memory/consent", {"enabled": True})
        reply = self.call("POST", "/api/chat", {"text": "My favorite color is green."})
        self.assertTrue(reply["memory_saved"])
        memory = self.call("GET", "/api/memory")["memories"][0]
        second = Application(self.config)
        try:
            self.assertEqual(second.memory.list_memories(OWNER)[0]["id"], memory["id"])
        finally:
            second.close()
        recalled = self.call("POST", "/api/chat", {"text": "What do you remember?"})
        self.assertIn("green", recalled["reply"].lower())
        self.call("POST", "/api/memory/consent", {"enabled": False})
        recalled = self.call("POST", "/api/chat", {"text": "What do you remember?"})
        self.assertNotIn("green", recalled["reply"].lower())
        self.assertEqual(len(self.call("GET", "/api/memory")["memories"]), 1)
        self.call("DELETE", "/api/memory/" + memory["id"])
        self.assertEqual(self.call("GET", "/api/memory")["memories"], [])

    def test_sensitive_memory_requires_ui_confirmation(self):
        self.call("POST", "/api/memory/consent", {"enabled": True})
        data = {"text": "Synthetic private medical note", "category": "preference"}
        with self.assertRaises(PermissionError):
            self.call("POST", "/api/memory", data)
        data["category"] = "sensitive"
        data["approved"] = True
        result = self.call("POST", "/api/memory", data)
        self.assertEqual(result["category"], "sensitive")
        data["text"] = "Corrected synthetic private note"
        self.call("PATCH", "/api/memory/" + result["id"], data)
        self.assertEqual(self.call("GET", "/api/memory")["memories"][0]["text"], data["text"])

    def test_home_permission_confirmation_outage_and_revocation(self):
        command = {"entity_id": "light.demo_lamp", "action": "turn_on", "request_id": "one"}
        self.assertEqual(self.call("POST", "/api/home/action", command)["status"], "denied")
        grant = self.call("POST", "/api/home/grants", {"entity_id": command["entity_id"], "action": "turn_on", "confirmation": True})
        pending = self.call("POST", "/api/home/action", command)
        self.assertEqual(pending["status"], "confirmation_required")
        command["confirmation_id"] = pending["confirmation_id"]
        self.assertEqual(self.call("POST", "/api/home/action", command)["status"], "verified")
        self.assertEqual(self.call("GET", "/api/home")["devices"][0]["state"], "on")
        self.call("POST", "/api/home/outage", {"offline": True})
        command = dict(command, request_id="two")
        command.pop("confirmation_id")
        pending = self.call("POST", "/api/home/action", command)
        command["confirmation_id"] = pending["confirmation_id"]
        self.assertEqual(self.call("POST", "/api/home/action", command)["status"], "unavailable")
        self.call("POST", "/api/home/outage", {"offline": False})
        self.assertEqual(self.call("POST", "/api/home/action", command)["status"], "unavailable")
        self.call("DELETE", "/api/home/grants/" + grant["id"])
        self.assertEqual(self.call("POST", "/api/home/action", dict(command, request_id="three"))["status"], "denied")

    def test_voice_is_disabled_and_no_mock_cloud_claim(self):
        with self.assertRaises(ApiError) as caught:
            self.call("POST", "/api/voice/session", {"sdp": "v=0", "audio_consent": True})
        self.assertEqual(caught.exception.code, "voice_not_configured")
        self.assertEqual(self.call("POST", "/api/chat", {"text": "hello"})["mode"], "demo")

    def test_cloud_voice_never_receives_memories(self):
        class Voice:
            offers = []
            def create_session(self, sdp):
                self.offers.append(sdp)
                return "v=0\r\nanswer"
        voice = Voice()
        app = Application(Config(data_dir=Path(self.directory.name), voice_enabled=True, api_key="synthetic"), voice=voice)
        try:
            app.memory.set_enabled(OWNER, True)
            app.memory.save(OWNER, "Private synthetic note", category="sensitive", approved=True)
            with self.assertRaises(ApiError):
                app.dispatch("POST", "/api/voice/session", {"sdp": "v=0", "audio_consent": False})
            result = app.dispatch("POST", "/api/voice/session", {"sdp": "v=0", "audio_consent": True})
            self.assertEqual(result["sdp"], "v=0\r\nanswer")
            self.assertEqual(voice.offers, ["v=0"])
        finally:
            app.close()

    def test_voice_offer_preserves_final_crlf_and_attribute_whitespace(self):
        voice = Mock()
        voice.create_session.return_value = "v=0\r\nsynthetic-answer\r\n"
        app = Application(Config(data_dir=Path(self.directory.name), voice_enabled=True,
                                 api_key="synthetic"), voice=voice)
        self.addCleanup(app.close)
        offer = ("v=0\r\no=- 12345 1 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n"
                 "a=x-synthetic-note:keep these trailing spaces  \r\n")
        result = app.dispatch("POST", "/api/voice/session", {"sdp": offer, "audio_consent": True})
        voice.create_session.assert_called_once_with(offer)
        self.assertEqual(result["sdp"], "v=0\r\nsynthetic-answer\r\n")

    def test_voice_offer_validation_precedes_provider_call(self):
        voice = Mock()
        app = Application(Config(data_dir=Path(self.directory.name), voice_enabled=True,
                                 api_key="synthetic"), voice=voice)
        self.addCleanup(app.close)
        for offer in (None, False, 123, "", " \r\n", "v=0" + "x" * 99998):
            with self.subTest(kind=type(offer).__name__), self.assertRaises(ValueError):
                app.dispatch("POST", "/api/voice/session", {"sdp": offer, "audio_consent": True})
        voice.create_session.assert_not_called()


if __name__ == "__main__":
    unittest.main()
