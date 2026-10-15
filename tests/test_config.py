import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from wanda.config import Config, ROOT, private_path


class ConfigTests(unittest.TestCase):
    def test_defaults_need_no_credentials(self):
        config = Config.load({"WANDA_CONFIG": ""})
        self.assertFalse(config.voice_enabled)
        self.assertEqual(config.api_key, "")
        self.assertEqual(config.home_mode, "mock")
        self.assertNotEqual(config.data_dir, ROOT)

    def test_private_data_never_under_checkout(self):
        for path in (ROOT, ROOT / "data", ROOT / "nested" / ".." / "data"):
            with self.assertRaises(ValueError):
                private_path(path)
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / "link"
            try:
                link.symlink_to(ROOT, target_is_directory=True)
            except OSError:
                self.skipTest("Symlink creation unavailable on this host")
            with self.assertRaises(ValueError):
                private_path(link / "runtime")

    def test_external_config_and_environment_override(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"WANDA_PORT": 8888, "WANDA_ENABLE_CLOUD_VOICE": True,
                                        "OPENAI_API_KEY": "synthetic-secret", "WANDA_DATA_DIR": directory}))
            config = Config.load({"WANDA_CONFIG": str(path), "WANDA_PORT": "9999"})
            self.assertEqual(config.port, 9999)
            self.assertTrue(config.voice_enabled)
            self.assertNotIn("synthetic-secret", repr(config))
            config.prepare()

    def test_invalid_configuration_rejected(self):
        for values in ({"WANDA_PORT": "80"}, {"WANDA_HOME_MODE": "anywhere"},
                       {"WANDA_CONFIG": str(ROOT / "config.example.json")},
                       {"WANDA_HOME_ENTITIES": [12]}):
            with self.assertRaises((ValueError, OSError)):
                Config.load(values)

    def test_private_default_config_and_explicit_disable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"WANDA_PORT": 9911}), encoding="utf-8")
            self.assertEqual(Config.load({"WANDA_DATA_DIR": directory}).port, 9911)
            self.assertEqual(Config.load({"WANDA_DATA_DIR": directory, "WANDA_CONFIG": ""}).port, 8765)

    def test_explicit_data_directory_needs_no_home_environment(self):
        with tempfile.TemporaryDirectory() as directory, patch("wanda.config.Path.home", side_effect=RuntimeError("No home directory")):
            config = Config.load({"WANDA_DATA_DIR": directory, "WANDA_CONFIG": ""})
            self.assertEqual(config.data_dir, Path(directory).resolve())

    def test_doctor_checks_adapter_configuration_without_network(self):
        from wanda.__main__ import main
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {
            "WANDA_CONFIG": "", "WANDA_DATA_DIR": directory,
            "WANDA_HOME_MODE": "homeassistant", "HOME_ASSISTANT_URL": "",
            "HOME_ASSISTANT_TOKEN": "", "WANDA_HOME_ENTITIES": "",
        }, clear=True):
            self.assertEqual(main(["--doctor"]), 1)

    def test_launcher_never_follows_redirects(self):
        from wanda.__main__ import NoRedirect
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.invalid"))

    def test_voice_setup_saves_private_config_without_network(self):
        from wanda.__main__ import configure_voice
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {}, clear=True):
            config = Config(data_dir=Path(directory))
            with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="yes"), patch("getpass.getpass", return_value="synthetic-test-key"):
                self.assertEqual(configure_voice(config), 0)
            loaded = Config.load({"WANDA_DATA_DIR": directory})
            self.assertTrue(loaded.voice_enabled)
            self.assertEqual(loaded.api_key, "synthetic-test-key")
            with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="disable"):
                self.assertEqual(configure_voice(config), 0)
            loaded = Config.load({"WANDA_DATA_DIR": directory})
            self.assertFalse(loaded.voice_enabled)
            self.assertEqual(loaded.api_key, "")


if __name__ == "__main__":
    unittest.main()
