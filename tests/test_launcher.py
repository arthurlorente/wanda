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

    def command(self, *args, timeout=10):
        return subprocess.run([sys.executable, "-m", "wanda", *args], cwd=ROOT, env=self.env,
                              text=True, capture_output=True, timeout=timeout, check=False)

    def start(self):
        process = subprocess.Popen([sys.executable, "-m", "wanda", "--no-browser"],
                                   cwd=ROOT, env=self.env, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.processes.append(process)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self.fail(f"Wanda launcher exited before serving (code {process.returncode})")
            try:
                status, data = self.api("GET", "/health", auth=False)
                if status == 200 and data.get("service") == "wanda":
                    return process
            except (OSError, TimeoutError, ValueError):
                pass
            time.sleep(0.1)
        self.fail("Wanda did not start within 12 seconds")

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


if __name__ == "__main__":
    unittest.main()
