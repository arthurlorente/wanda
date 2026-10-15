"""Start/stop smoke test using a private temporary folder and no providers."""

import http.client
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parent.parent


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wanda-launch-test-")
        # Use an explicit small environment: never inherit a developer's real keys,
        # private config file, or Home Assistant settings.
        self.env = {name: os.environ[name] for name in
                    ("PATH", "SYSTEMROOT", "WINDIR", "TMPDIR", "TEMP", "TMP") if name in os.environ}
        self.env.update({
            "WANDA_DATA_DIR": self.temp.name,
            "WANDA_PORT": str(self._free_port()),
            "WANDA_ENABLE_CLOUD_VOICE": "false",
            "WANDA_HOME_MODE": "mock",
            "PYTHONUNBUFFERED": "1",
        })
        self.port = int(self.env["WANDA_PORT"])
        self.processes = []

    @staticmethod
    def _free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            return listener.getsockname()[1]

    def tearDown(self):
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            if process.stdout is not None:
                process.stdout.close()
        self.temp.cleanup()

    def command(self, *args, timeout=10, env=None):
        return subprocess.run([sys.executable, "-m", "wanda", *args], cwd=ROOT,
                              env=self.env if env is None else env,
                              text=True, capture_output=True, timeout=timeout, check=False)

    def start(self):
        process = subprocess.Popen([sys.executable, "-m", "wanda", "--no-browser"],
                                   cwd=ROOT, env=self.env, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.processes.append(process)
        deadline = time.monotonic() + 12
        state_path = Path(self.temp.name) / "launcher.json"
        last_health = "not attempted"
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self.fail(f"Wanda launcher exited before serving (code {process.returncode})")
            # The launcher writes its private state after LocalServer finishes
            # binding. Polling an unready socket can fill its listen backlog.
            if state_path.exists():
                try:
                    status, data = self.api("GET", "/health", auth=False)
                    last_health = f"HTTP {status}"
                    if status == 200 and data.get("service") == "wanda":
                        return process
                except (OSError, TimeoutError, ValueError) as error:
                    last_health = type(error).__name__
            time.sleep(0.1)
        self.fail("Wanda did not start within 12 seconds "
                  f"(process_alive={process.poll() is None}, private_state_created={state_path.exists()}, "
                  f"last_health={last_health})")

    def capability(self):
        state_path = Path(self.temp.name) / "launcher.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["port"], self.port)
        self.assertEqual(len(state["token"]), 43)
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(state_path.stat().st_mode), 0o600)
        return state

    def api(self, method, path, data=None, *, auth=True):
        state = self.capability() if auth else None
        headers = {"Host": f"127.0.0.1:{self.port}"}
        if state is not None:
            headers["Authorization"] = "Bearer " + state["token"]
        body = None if data is None else json.dumps(data).encode("utf-8")
        if body is not None:
            headers["Content-Type"] = "application/json"
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_start_existing_stop_and_restart_preserve_memory(self):
        process = self.start()
        first = self.capability()
        status, data = self.api("GET", "/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(data["mode"], "demo")
        self.assertEqual(data["home"]["mode"], "mock")
        self.assertFalse(data["voice"]["configured"])
        status, _ = self.api("POST", "/api/memory/consent", {"enabled": True})
        self.assertEqual(status, 200)
        status, memory = self.api("POST", "/api/memory", {
            "text": "Synthetic preference: jasmine tea", "category": "preference", "approved": True,
        })
        self.assertEqual(status, 200)

        second_launch = self.command("--no-browser")
        self.assertEqual(second_launch.returncode, 0)
        self.assertTrue("already running" in second_launch.stdout, "Second launch did not detect the active server")
        second = self.capability()
        self.assertEqual(second["pid"], first["pid"])
        self.assertTrue(first["token"] == second["token"], "Existing capability unexpectedly changed")
        self.assertIsNone(process.poll())

        stop = self.command("--stop")
        self.assertEqual(stop.returncode, 0)
        self.assertTrue("stopping" in stop.stdout, "Stop command did not report shutdown")
        process.wait(timeout=10)
        self.assertFalse(first["token"] in second_launch.stdout + second_launch.stderr + stop.stdout + stop.stderr,
                         "Launch capability appeared in process output")
        self.assertFalse((Path(self.temp.name) / "launcher.json").exists())

        restarted = self.start()
        self.assertIsNone(restarted.poll())
        status, data = self.api("GET", "/api/memory")
        self.assertEqual(status, 200)
        self.assertTrue(data["enabled"])
        self.assertTrue(any(item["id"] == memory["id"] for item in data["memories"]))
        stop = self.command("--stop")
        self.assertEqual(stop.returncode, 0)
        restarted.wait(timeout=10)

    def test_stop_uses_explicit_data_folder_when_config_becomes_malformed(self):
        process = self.start()
        (Path(self.temp.name) / "config.json").write_text("{ malformed synthetic config", encoding="utf-8")
        stopped = self.command("--stop")
        self.assertEqual(stopped.returncode, 0)
        self.assertIn("stopping", stopped.stdout)
        process.wait(timeout=10)

    def test_stop_ignores_unrelated_invalid_settings_in_selected_config(self):
        process = self.start()
        selected = Path(self.temp.name) / "selected-config.json"
        selected.write_text(json.dumps({
            "WANDA_DATA_DIR": self.temp.name,
            "WANDA_PORT": "invalid-port", "WANDA_HOME_MODE": "invalid-home",
            "WANDA_VOICE_MODEL": 42,
        }), encoding="utf-8")
        env = dict(self.env)
        env.pop("WANDA_DATA_DIR")
        env.pop("WANDA_PORT")
        env["WANDA_CONFIG"] = str(selected)
        stopped = self.command("--stop", env=env)
        self.assertEqual(stopped.returncode, 0)
        self.assertIn("stopping", stopped.stdout)
        process.wait(timeout=10)

    def test_stop_never_scans_other_data_folders_or_guesses_explicit_config(self):
        process = self.start()
        selected = Path(self.temp.name) / "broken-selected.json"
        selected.write_text("{ malformed synthetic config", encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="wanda-wrong-stop-target-") as wrong_folder:
            wrong_env = dict(self.env)
            wrong_env["WANDA_DATA_DIR"] = wrong_folder
            wrong_env["WANDA_CONFIG"] = str(selected)
            wrong = self.command("--stop", env=wrong_env)
            self.assertEqual(wrong.returncode, 0)
            self.assertIn("already stopped", wrong.stdout)
            self.assertIsNone(process.poll())
        uncertain_env = dict(self.env)
        uncertain_env.pop("WANDA_DATA_DIR")
        uncertain_env["WANDA_CONFIG"] = str(selected)
        uncertain = self.command("--stop", env=uncertain_env)
        self.assertEqual(uncertain.returncode, 1)
        self.assertIn("could not identify the data folder", uncertain.stderr)
        self.assertIn("WANDA_DATA_DIR", uncertain.stderr)
        self.assertIsNone(process.poll())
        stopped = self.command("--stop")
        self.assertEqual(stopped.returncode, 0)
        process.wait(timeout=10)

    def test_stop_reports_existing_invalid_launcher_state_as_unverified(self):
        process = self.start()
        state_path = Path(self.temp.name) / "launcher.json"
        for bad_state in ("{ invalid synthetic state", "[]", "null",
                          json.dumps({"port": "not-a-port", "token": "synthetic"}),
                          json.dumps({"port": self.port, "token": None}),
                          json.dumps({"port": self.port, "token": "wrong-synthetic-token"})):
            with self.subTest(bad_state=bad_state[:20]):
                state_path.write_text(bad_state, encoding="utf-8")
                stopped = self.command("--stop")
                self.assertEqual(stopped.returncode, 1)
                self.assertIn("cannot verify or stop", stopped.stderr)
                self.assertIn("Control+C", stopped.stderr)
                self.assertNotIn("already stopped", stopped.stdout + stopped.stderr)
                self.assertIsNone(process.poll())

    def test_stop_distinguishes_absent_and_stale_unreachable_launcher_state(self):
        absent = self.command("--stop")
        self.assertEqual(absent.returncode, 0)
        self.assertIn("already stopped", absent.stdout)
        state_path = Path(self.temp.name) / "launcher.json"
        state_path.write_text(json.dumps({
            "port": self.port, "token": "stale-synthetic-token", "pid": 123,
        }), encoding="utf-8")
        stale = self.command("--stop")
        self.assertEqual(stale.returncode, 1)
        self.assertIn("cannot verify or stop", stale.stderr)
        self.assertNotIn("already stopped", stale.stdout + stale.stderr)

    @unittest.skipIf(os.name == "nt", "Windows terminate bypasses Python's signal cleanup handler")
    def test_signal_shutdown_keeps_nonobject_launcher_state_without_traceback(self):
        state_path = Path(self.temp.name) / "launcher.json"
        for invalid_state in ("[]", "null"):
            with self.subTest(invalid_state=invalid_state):
                process = self.start()
                state_path.write_text(invalid_state, encoding="utf-8")
                process.terminate()
                self.assertEqual(process.wait(timeout=10), 0)
                output = process.stdout.read() if process.stdout is not None else ""
                self.assertNotIn("Traceback", output)
                self.assertEqual(state_path.read_text(encoding="utf-8"), invalid_state)


if __name__ == "__main__":
    unittest.main()
