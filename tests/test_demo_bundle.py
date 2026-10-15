"""Synthetic Git snapshots and an unpacked, offline demo; no provider requests."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

from scripts.build_demo import ARCHIVE_ROOT, BundleError, ROOT, _git, build_bundle


@unittest.skipUnless(shutil.which("git"), "Git is needed only for developer bundle tests")
class DemoBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wanda-bundle-test-")
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "synthetic-repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q")
        self.files = {
            "README.md": b"Committed synthetic README\n", "SECURITY.md": b"Synthetic security guide\n",
            ".env.example": b"OPENAI_API_KEY=\n", "config.example.json": b"{}\n",
            "docs/MORNING_HANDOFF.md": b"Synthetic walkthrough\n",
            "docs/adr/0008-v0-portable-stack.md": b"Python standard library\n",
            "web/index.html": b"<!doctype html><title>Synthetic Wanda</title>\n",
            "web/app.js": b"'use strict';\n", "web/backup.js": b"'use strict';\n",
            "web/styles.css": b"body {}\n", "scripts/wanda.sh": b"#!/bin/sh\npython3 -m wanda\n",
            ".gitignore": b"dist/\n.env\nprivate/\n*.sqlite3\n__pycache__/\n",
        }
        for name in ("Start Wanda", "Stop Wanda", "Configure Voice"):
            self.files[name + ".command"] = b"#!/bin/sh\nsh scripts/wanda.sh\n"
            self.files[name + ".bat"] = b"@echo off\r\npython -m wanda\r\n"
        for module in ("__init__", "__main__", "config", "server", "memory", "home", "persona", "voice", "tls"):
            self.files[f"wanda/{module}.py"] = b'"""Synthetic committed module."""\n'
        for name, data in self.files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        _git(self.repo, "add", ".")
        # Set index modes explicitly so this fixture also works on Windows.
        _git(self.repo, "update-index", "--chmod=+x", "Start Wanda.command", "Stop Wanda.command",
             "Configure Voice.command", "scripts/wanda.sh")
        self._commit()

    def tearDown(self):
        self.temp.cleanup()

    def _commit(self):
        _git(self.repo, "-c", "user.name=Synthetic bundle test", "-c", "user.email=bundle@example.invalid",
             "-c", "commit.gpgsign=false", "commit", "-qm", "Synthetic fixture")
        return _git(self.repo, "rev-parse", "HEAD").decode().strip()

    def _build(self, name="demo.zip", **kwargs):
        return build_bundle(self.repo, output=self.base / name, **kwargs)

    def test_commit_only_manifest_and_private_workspace_exclusions(self):
        committed_readme = self.files["README.md"]
        (self.repo / "README.md").write_bytes(b"UNCOMMITTED PRIVATE TEXT")
        # Even staged changes are excluded by reading committed blobs.
        _git(self.repo, "add", "README.md")
        for name in (".env", "private/config.json", "wanda/local.sqlite3", "web/untracked.js", "docs/untracked.md"):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"SYNTHETIC_PRIVATE_DO_NOT_SHIP")
        result = self._build()
        with zipfile.ZipFile(result["archive"]) as archive:
            names = archive.namelist()
            self.assertTrue(all(name.startswith(ARCHIVE_ROOT + "/") for name in names))
            self.assertEqual(archive.read("Wanda/README.md"), committed_readme)
            self.assertIn("Wanda/config.example.json", names)
            self.assertIn("Wanda/.env.example", names)
            self.assertIn("Wanda/docs/MORNING_HANDOFF.md", names)
            self.assertIn("Wanda/scripts/wanda.sh", names)
            for name in names:
                self.assertNotIn("/.git", name)
                self.assertNotIn(b"SYNTHETIC_PRIVATE_DO_NOT_SHIP", archive.read(name))
                self.assertNotIn(b"UNCOMMITTED PRIVATE TEXT", archive.read(name))
            self.assertFalse(any(name.endswith("local.sqlite3") or "untracked" in name for name in names))
            manifest = json.loads(archive.read("Wanda/BUILD_INFO.json"))
            self.assertEqual(manifest["commit"], result["commit"])
            self.assertEqual(manifest["format"], "wanda-demo-bundle")
            self.assertEqual(manifest["python_required"], ">=3.11")
            self.assertFalse(manifest["python_included"])
            self.assertEqual({item["path"] for item in manifest["files"]},
                             {name.removeprefix("Wanda/") for name in names} - {"BUILD_INFO.json"})
            for item in manifest["files"]:
                self.assertEqual(hashlib.sha256(archive.read("Wanda/" + item["path"])).hexdigest(), item["sha256"])

    def test_deterministic_output_and_committed_executable_permissions(self):
        first = self._build("first.zip")
        for name in self.files:
            os.utime(self.repo / name, (1_000_000_000, 1_000_000_000))
        second = self._build("second.zip", ref=first["commit"])
        self.assertEqual(Path(first["archive"]).read_bytes(), Path(second["archive"]).read_bytes())
        self.assertEqual(first["sha256"], second["sha256"])
        with zipfile.ZipFile(first["archive"]) as archive:
            self.assertEqual(archive.namelist(), sorted(archive.namelist()))
            for name in ("Start Wanda.command", "Stop Wanda.command", "Configure Voice.command", "scripts/wanda.sh"):
                entry = archive.getinfo("Wanda/" + name)
                self.assertEqual(entry.create_system, 3)
                self.assertEqual(stat.S_IMODE(entry.external_attr >> 16), 0o755)
            self.assertEqual(stat.S_IMODE(archive.getinfo("Wanda/config.example.json").external_attr >> 16), 0o644)

    def test_local_git_replacements_cannot_change_committed_bundle_content(self):
        original = _git(self.repo, "rev-parse", "HEAD:README.md").decode().strip()
        replacement = self.base / "replacement.txt"
        replacement.write_bytes(b"SYNTHETIC LOCAL REPLACEMENT MUST NOT SHIP")
        substitute = _git(self.repo, "hash-object", "-w", str(replacement)).decode().strip()
        _git(self.repo, "replace", original, substitute)
        result = self._build()
        with zipfile.ZipFile(result["archive"]) as archive:
            self.assertEqual(archive.read("Wanda/README.md"), self.files["README.md"])

    def test_default_output_is_ignored_and_existing_file_is_never_overwritten(self):
        result = build_bundle(self.repo)
        destination = Path(result["archive"])
        self.assertEqual(destination.parent, self.repo / "dist")
        self.assertEqual(_git(self.repo, "check-ignore", destination.name, "dist/" + destination.name).decode().strip(),
                         "dist/" + destination.name)
        original = destination.read_bytes()
        with self.assertRaises(BundleError):
            build_bundle(self.repo)
        self.assertEqual(destination.read_bytes(), original)
        unrelated = self.base / "unrelated.zip"
        unrelated.write_bytes(b"DO NOT OVERWRITE")
        with self.assertRaises(BundleError):
            build_bundle(self.repo, output=unrelated)
        self.assertEqual(unrelated.read_bytes(), b"DO NOT OVERWRITE")

    def test_committed_runtime_files_and_developer_harness_are_excluded(self):
        for name in ("wanda/private/notes.py", "wanda/memory.sqlite3", "docs/private/notes.md",
                     "web/.env", "scripts/live_voice_check.py", "tests/test_example.py"):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"SYNTHETIC_EXCLUDED_FIXTURE")
            _git(self.repo, "add", "-f", name)
        self._commit()
        result = self._build()
        with zipfile.ZipFile(result["archive"]) as archive:
            self.assertFalse(any(b"SYNTHETIC_EXCLUDED_FIXTURE" in archive.read(name) for name in archive.namelist()))

    def test_old_commit_selection_and_invalid_or_incomplete_revision(self):
        old = _git(self.repo, "rev-parse", "HEAD").decode().strip()
        (self.repo / "README.md").write_bytes(b"Second committed README")
        _git(self.repo, "add", "README.md")
        self._commit()
        result = self._build(ref=old)
        with zipfile.ZipFile(result["archive"]) as archive:
            self.assertEqual(archive.read("Wanda/README.md"), self.files["README.md"])
        with self.assertRaises(BundleError):
            self._build("invalid.zip", ref="--help")
        _git(self.repo, "rm", "web/index.html")
        self._commit()
        with self.assertRaises(BundleError):
            self._build("incomplete.zip")
        self.assertFalse((self.base / "invalid.zip").exists())
        self.assertFalse((self.base / "incomplete.zip").exists())

    def test_missing_launcher_execute_bit_is_rejected(self):
        _git(self.repo, "update-index", "--chmod=-x", "Start Wanda.command")
        self._commit()
        with self.assertRaisesRegex(BundleError, "executable permissions"):
            self._build()

    def test_embedded_git_dependency_is_rejected_without_fetching_it(self):
        commit = _git(self.repo, "rev-parse", "HEAD").decode().strip()
        _git(self.repo, "update-index", "--add", "--cacheinfo", f"160000,{commit},web/vendor")
        self._commit()
        with self.assertRaisesRegex(BundleError, "submodules"):
            self._build()
        self.assertFalse((self.base / "demo.zip").exists())

    @unittest.skipIf(os.name == "nt", "Creating symlinks may require Windows developer privileges")
    def test_selected_symlink_and_implicit_output_redirect_are_rejected(self):
        (self.repo / "web/private.js").symlink_to(self.base / "outside.js")
        _git(self.repo, "add", "web/private.js")
        self._commit()
        with self.assertRaisesRegex(BundleError, "regular committed files"):
            self._build()
        _git(self.repo, "rm", "web/private.js")
        self._commit()
        outside = self.base / "outside"
        outside.mkdir()
        (self.repo / "dist").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(BundleError):
            build_bundle(self.repo)
        self.assertEqual(list(outside.iterdir()), [])
        existing = self.base / "link.zip"
        protected = self.base / "protected.txt"
        protected.write_text("Synthetic protected file", encoding="utf-8")
        existing.symlink_to(protected)
        with self.assertRaises(BundleError):
            build_bundle(self.repo, output=existing)
        self.assertEqual(protected.read_text(encoding="utf-8"), "Synthetic protected file")

    def test_extracted_committed_application_runs_doctor_without_git(self):
        # HEAD is read from Git, not from concurrently edited application files.
        result = build_bundle(ROOT, output=self.base / "real-demo.zip")
        extracted = self.base / "extracted"
        with zipfile.ZipFile(result["archive"]) as archive:
            archive.extractall(extracted)
        application = extracted / ARCHIVE_ROOT
        self.assertFalse((application / ".git").exists())
        private = self.base / "synthetic-private"
        private.mkdir()
        config = private / "config.json"
        config.write_text(json.dumps({"WANDA_DATA_DIR": str(private), "WANDA_HOME_MODE": "mock",
                                      "WANDA_ENABLE_CLOUD_VOICE": False, "OPENAI_API_KEY": ""}), encoding="utf-8")
        no_tools = self.base / "empty-path"
        no_tools.mkdir()
        environment = {name: os.environ[name] for name in ("SYSTEMROOT", "WINDIR", "TMPDIR", "TEMP", "TMP")
                       if name in os.environ}
        environment.update({"PATH": str(no_tools), "WANDA_CONFIG": str(config),
                            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"})
        self.assertIsNone(shutil.which("git", path=environment["PATH"]))
        process = subprocess.run([sys.executable, "-m", "wanda", "--doctor"], cwd=application,
                                 env=environment, capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertIn("Runtime packages: none required", process.stdout)
        self.assertIn("Cloud voice: off", process.stdout)
        self.assertIn("Home: mock", process.stdout)
        self.assertIn("no provider or home connection attempted", process.stdout)


if __name__ == "__main__":
    unittest.main()
