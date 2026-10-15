import ssl
from pathlib import Path
import unittest
from unittest.mock import patch

from wanda.tls import create_https_context


class TLSTests(unittest.TestCase):
    def assert_verified(self, context):
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)

    def test_loaded_default_trust_is_preserved_on_every_platform(self):
        for platform in ("darwin", "linux", "win32"):
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            with self.subTest(platform=platform), \
                    patch("wanda.tls.ssl.create_default_context", return_value=context) as factory, \
                    patch("wanda.tls.sys.platform", platform), \
                    patch.object(context, "get_ca_certs", return_value=[{"subject": "default CA"}]), \
                    patch("wanda.tls.Path.is_file") as is_file, \
                    patch.object(context, "load_verify_locations") as load:
                self.assertIs(create_https_context(), context)
                factory.assert_called_once_with()
                is_file.assert_not_called()
                load.assert_not_called()
                self.assert_verified(context)

    def test_macos_empty_default_uses_only_fixed_system_bundle(self):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        with patch("wanda.tls.ssl.create_default_context", return_value=context), \
                patch("wanda.tls.sys.platform", "darwin"), \
                patch("wanda.tls.Path.is_file", return_value=True), \
                patch.object(context, "load_verify_locations") as load:
            self.assertIs(create_https_context(), context)
            # sys.platform is mocked; Path still uses this test host's separators.
            load.assert_called_once_with(cafile=str(Path("/etc/ssl/cert.pem")))
            self.assert_verified(context)

    def test_empty_non_macos_store_does_not_use_fallback(self):
        for platform in ("linux", "win32"):
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            with self.subTest(platform=platform), \
                    patch("wanda.tls.ssl.create_default_context", return_value=context), \
                    patch("wanda.tls.sys.platform", platform), \
                    patch("wanda.tls.Path.is_file") as is_file:
                self.assertIs(create_https_context(), context)
                is_file.assert_not_called()
                self.assertEqual(context.get_ca_certs(), [])
                self.assert_verified(context)

    def test_missing_system_bundle_keeps_verified_context(self):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        with patch("wanda.tls.ssl.create_default_context", return_value=context), \
                patch("wanda.tls.sys.platform", "darwin"), \
                patch("wanda.tls.Path.is_file", return_value=False), \
                patch.object(context, "load_verify_locations") as load:
            self.assertIs(create_https_context(), context)
            load.assert_not_called()
            self.assertEqual(context.get_ca_certs(), [])
            self.assert_verified(context)

    def test_unreadable_or_invalid_bundle_never_disables_verification(self):
        for error in (OSError("unreadable bundle"), ssl.SSLError("invalid bundle")):
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            with self.subTest(error=type(error)), \
                    patch("wanda.tls.ssl.create_default_context", return_value=context), \
                    patch("wanda.tls.sys.platform", "darwin"), \
                    patch("wanda.tls.Path.is_file", return_value=True), \
                    patch.object(context, "load_verify_locations", side_effect=error):
                self.assertIs(create_https_context(), context)
                self.assertEqual(context.get_ca_certs(), [])
                self.assert_verified(context)

    def test_real_context_requires_certificate_and_hostname_checks(self):
        self.assert_verified(create_https_context())


if __name__ == "__main__":
    unittest.main()
