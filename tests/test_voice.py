import email.parser
import io
import json
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from wanda.voice import ENDPOINT, MAX_SDP_BYTES, VoiceProvider, _NoRedirect


class Response(io.BytesIO):
    status = 201


class VoiceTests(unittest.TestCase):
    def test_sdp_exchange_has_persona_no_tools_and_no_memory(self):
        calls = []
        def transport(request, timeout):
            calls.append((request, timeout))
            return Response(b"v=0\r\nmock-answer\r\n")
        answer = VoiceProvider("synthetic-test-key", transport=transport).create_session("v=0\r\nmock-offer\r\n")
        self.assertEqual(answer, "v=0\r\nmock-answer\r\n")
        request, timeout = calls[0]
        self.assertEqual(request.full_url, ENDPOINT)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(timeout, 25)
        self.assertEqual(request.get_header("Authorization"), "Bearer synthetic-test-key")
        mime = email.parser.BytesParser().parsebytes(("Content-Type: " + request.get_header("Content-type") + "\r\n\r\n").encode() + request.data)
        parts = {part.get_param("name", header="content-disposition"): part.get_payload(decode=True).decode() for part in mime.get_payload()}
        self.assertEqual(parts["sdp"], "v=0\r\nmock-offer\r\n")
        session = json.loads(parts["session"])
        self.assertEqual(session["model"], "gpt-realtime-2.1")
        self.assertEqual(session["tools"], [])
        self.assertNotIn("format", session["audio"]["input"])
        self.assertNotIn("transcription", session["audio"]["input"])
        self.assertTrue(session["audio"]["input"]["turn_detection"]["interrupt_response"])
        self.assertEqual(session["audio"]["input"]["turn_detection"]["eagerness"], "low")
        self.assertIn("No saved local memories", session["instructions"])
        self.assertLessEqual(session["max_output_tokens"], 1024)

    def test_invalid_offers_never_use_transport(self):
        def forbidden(*args, **kwargs):
            self.fail("Transport must not be called")
        provider = VoiceProvider("synthetic", transport=forbidden)
        for value in (None, "", "hello", "v=0" + "x" * MAX_SDP_BYTES):
            with self.subTest(value=str(value)[:30]), self.assertRaises(ValueError):
                provider.create_session(value)

    def test_default_transport_uses_verified_https_context(self):
        with patch("wanda.voice.create_https_context") as context, \
                patch("wanda.voice.urllib.request.HTTPSHandler") as https_handler, \
                patch("wanda.voice.urllib.request.build_opener") as opener:
            provider = VoiceProvider("synthetic")
            context.assert_called_once_with()
            https_handler.assert_called_once_with(context=context.return_value)
            handlers = opener.call_args.args
            self.assertIsInstance(handlers[0], urllib.request.ProxyHandler)
            self.assertEqual(handlers[0].proxies, {})
            self.assertIsInstance(handlers[1], _NoRedirect)
            self.assertIs(handlers[2], https_handler.return_value)
            self.assertIs(provider._transport, opener.return_value.open)

    def test_trusted_test_subclass_controls_session_without_browser_overrides(self):
        class SmokeProvider(VoiceProvider):
            def _session_config(self):
                config = super()._session_config()
                config["max_output_tokens"] = 128
                config["audio"]["input"]["turn_detection"] = None
                config["reasoning"] = {"effort": "minimal"}
                config["tool_choice"] = "none"
                config["tracing"] = None
                return config

        requests = []
        def transport(request, timeout):
            requests.append(request)
            return Response(b"v=0\r\nmock-answer\r\n")
        SmokeProvider("synthetic", transport=transport).create_session("v=0\r\nmock-offer\r\n")
        request = requests[0]
        mime = email.parser.BytesParser().parsebytes(("Content-Type: " + request.get_header("Content-type") + "\r\n\r\n").encode() + request.data)
        parts = {part.get_param("name", header="content-disposition"): part.get_payload(decode=True).decode() for part in mime.get_payload()}
        session = json.loads(parts["session"])
        self.assertEqual(session["max_output_tokens"], 128)
        self.assertIsNone(session["audio"]["input"]["turn_detection"])
        self.assertEqual(session["reasoning"], {"effort": "minimal"})
        self.assertEqual(session["tool_choice"], "none")
        self.assertIsNone(session["tracing"])
        default = VoiceProvider("synthetic", transport=transport)._session_config()
        self.assertEqual(default["max_output_tokens"], 1024)
        self.assertEqual(default["audio"]["input"]["turn_detection"]["type"], "semantic_vad")

    def test_missing_key_never_uses_transport(self):
        provider = VoiceProvider("", transport=lambda *args, **kwargs: self.fail("No transport without key"))
        with self.assertRaisesRegex(RuntimeError, "not configured"):
            provider.create_session("v=0")

    def test_http_errors_are_sanitized(self):
        for code, expected in ((401, "access was denied"), (403, "access was denied"), (429, "limit"), (500, "could not connect"), (302, "could not connect")):
            def transport(*args, **kwargs):
                raise urllib.error.HTTPError(ENDPOINT, code, "SECRET private transcript", {}, io.BytesIO(b"private payload"))
            with self.subTest(code=code), self.assertRaises(RuntimeError) as result:
                VoiceProvider("synthetic-key", transport=transport).create_session("v=0")
            self.assertIn(expected, str(result.exception))
            self.assertNotIn("SECRET", str(result.exception))
            self.assertNotIn("private", str(result.exception))

    def test_network_failure_is_sanitized(self):
        for error in (TimeoutError("secret"), urllib.error.URLError("private address"), OSError("secret")):
            def transport(*args, **kwargs):
                raise error
            with self.subTest(error=type(error)), self.assertRaisesRegex(RuntimeError, "unavailable"):
                VoiceProvider("synthetic", transport=transport).create_session("v=0")

    def test_invalid_answers_are_rejected(self):
        for answer in (b"private provider error", b"v=0" + b"x" * MAX_SDP_BYTES, b"\xff"):
            with self.subTest(size=len(answer)), self.assertRaises(RuntimeError):
                VoiceProvider("synthetic", transport=lambda *args, **kwargs: Response(answer)).create_session("v=0")

    def test_config_cannot_inject_headers(self):
        for key, model in (("key\nHeader: injected", "model"), ("key", "../bad"), (None, "model")):
            with self.subTest(model=model), self.assertRaises(ValueError):
                VoiceProvider(key, model)

    def test_redirects_never_forward_credentials(self):
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example"))


if __name__ == "__main__":
    unittest.main()
