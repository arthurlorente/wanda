"""Build a reproducible source/demo ZIP from a reviewed, committed Git tree.

Developer-only: Python 3.11+ and Git are needed to build; the unpacked demo only
needs Python 3.11+. This is not a Python installer. No configuration, credentials,
working-tree files or runtime data are read. Committed source must still be
reviewed before distribution: this builder is not a secret scanner.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_ROOT = "Wanda"
_FIXED_TIME = (1980, 1, 1, 0, 0, 0)
_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_ROOT_FILES = frozenset({
    "README.md", "SECURITY.md", "CONTRIBUTING.md", "AGENTS.md", "pyproject.toml",
    ".env.example", "config.example.json", "Start Wanda.command", "Start Wanda.bat",
    "Stop Wanda.command", "Stop Wanda.bat", "Configure Voice.command", "Configure Voice.bat",
})
_PRIVATE_DIRS = frozenset({
    "__pycache__", "node_modules", "secrets", "private", "runtime", "data",
    "memory", "transcripts", "recordings", "dist", "build",
})
_WEB_SUFFIXES = frozenset({".html", ".css", ".js", ".svg", ".png", ".ico", ".jpg", ".jpeg", ".webp", ".woff", ".woff2"})
_REQUIRED = frozenset({
    "README.md", "SECURITY.md", ".env.example", "config.example.json",
    "Start Wanda.command", "Start Wanda.bat", "Stop Wanda.command", "Stop Wanda.bat",
    "Configure Voice.command", "Configure Voice.bat", "scripts/wanda.sh",
    "docs/MORNING_HANDOFF.md", "wanda/__init__.py", "wanda/__main__.py",
    "wanda/config.py", "wanda/server.py", "wanda/memory.py", "wanda/home.py",
    "wanda/persona.py", "wanda/voice.py", "wanda/tls.py",
    "web/index.html", "web/app.js", "web/backup.js", "web/styles.css",
})
_EXECUTABLES = frozenset({"Start Wanda.command", "Stop Wanda.command", "Configure Voice.command", "scripts/wanda.sh"})
_START_HERE = """Wanda V0 demonstration

Unzip the entire archive before starting Wanda. Keep the files together.
Python 3.11 or newer must already be installed. This ZIP does not install Python.
Git, extra Python packages, a GPU and an API key are not needed for the local demo.

Mac: double-click Start Wanda.command.
Windows: double-click Start Wanda.bat.
Linux: open a terminal in this folder and run: python3 -m wanda

The launcher opens your browser. Keep its terminal window open while using Wanda.
Use Stop Wanda or Control+C in that terminal when finished.
Read docs/MORNING_HANDOFF.md for the walkthrough and current limitations.

Local chat is scripted. Memory is real and opt-in. Home devices are simulated by
default. Optional cloud voice requires separate setup and per-session consent.
Private configuration and memory belong outside this extracted folder.
BUILD_INFO.json identifies the exact source commit and file checksums.
""".encode("utf-8")


class BundleError(ValueError):
    """A safe, actionable build failure with no Git stderr or private content."""


def _git(repo, *arguments):
    # No user Git config, credential helpers, external filters or network command.
    environment = {key: os.environ[key] for key in
                   ("PATH", "SYSTEMROOT", "WINDIR", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL")
                   if key in os.environ}
    environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                        "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0",
                        "GIT_NO_REPLACE_OBJECTS": "1"})
    try:
        result = subprocess.run(["git", "-C", str(repo), *arguments],
                                env=environment, capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise BundleError("Git is required to build the demo; check the repository and Git installation.") from None
    if result.returncode:
        raise BundleError("Git could not read the requested committed snapshot.")
    return result.stdout


def _included(name):
    if name in _ROOT_FILES or name == "scripts/wanda.sh":
        return True
    path = PurePosixPath(name)
    if len(path.parts) < 2 or any(part.startswith(".") or part in _PRIVATE_DIRS for part in path.parts):
        return False
    return ((path.parts[0] == "wanda" and path.suffix == ".py") or
            (path.parts[0] == "docs" and path.suffix == ".md") or
            (path.parts[0] == "web" and path.suffix in _WEB_SUFFIXES))


def _portable_path(name):
    path = PurePosixPath(name)
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if (path.is_absolute() or str(path) != name or "\\" in name or
            any(ord(char) < 32 or ord(char) == 127 or char in ':<>"|?*' for char in name) or
            any(part in {".", ".."} or part.endswith((".", " ")) or
                part.split(".")[0].upper() in reserved for part in path.parts)):
        raise BundleError("The snapshot contains a path that cannot be safely packaged across platforms.")


def _snapshot(repo, ref):
    if not isinstance(ref, str) or not ref or len(ref) > 1024 or any(ord(char) < 32 for char in ref):
        raise BundleError("Choose a committed Git revision, such as HEAD or a commit identifier.")
    commit = _git(repo, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode("ascii").strip()
    if not _OBJECT_ID.fullmatch(commit):
        raise BundleError("Git did not return a valid commit identifier.")
    files = {}
    folded = set()
    for entry in _git(repo, "ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0"):
        if not entry:
            continue
        metadata, raw_name = entry.split(b"\t", 1)
        name = raw_name.decode("utf-8")
        mode, kind, identifier = metadata.decode("ascii").split()
        if (kind == "commit" or mode == "120000") and name.partition("/")[0] in {"wanda", "web", "docs"}:
            raise BundleError("Bundle files must be regular committed files, not symbolic links or submodules.")
        if not _included(name):
            continue
        _portable_path(name)
        if name.casefold() in folded:
            raise BundleError("The snapshot contains paths that collide on case-insensitive computers.")
        folded.add(name.casefold())
        if kind != "blob" or mode not in {"100644", "100755"} or not _OBJECT_ID.fullmatch(identifier):
            raise BundleError("Bundle files must be regular committed files, not symbolic links or submodules.")
        files[name] = (_git(repo, "cat-file", "blob", identifier), int(mode, 8))
    if not _REQUIRED.issubset(files):
        raise BundleError("The selected snapshot is missing required Wanda demo files.")
    if any(not files[name][1] & stat.S_IXUSR for name in _EXECUTABLES):
        raise BundleError("Commit executable permissions for the Mac launchers and scripts/wanda.sh first.")
    return commit, files


def build_bundle(repo=ROOT, ref="HEAD", output=None):
    """Return build metadata after writing a new ZIP; never overwrite a file.

    ``output`` explicitly opts into that path, including outside the repository.
    The implicit output is confined to the repository's ignored ``dist`` folder.
    Git tree/blob operations exclude staged changes and all working-tree files.
    """
    repo = Path(repo).resolve()
    commit, files = _snapshot(repo, ref)
    files["START_HERE.txt"] = (_START_HERE, stat.S_IFREG | 0o644)
    manifest = {
        "format": "wanda-demo-bundle", "version": 1, "commit": commit,
        "python_required": ">=3.11", "python_included": False,
        "files": [{"path": name, "sha256": hashlib.sha256(data).hexdigest(), "mode": format(mode, "06o")}
                  for name, (data, mode) in sorted(files.items())],
    }
    files["BUILD_INFO.json"] = ((json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"),
                                stat.S_IFREG | 0o644)
    if output is None:
        folder = repo / "dist"
        if folder.resolve() != folder:
            raise BundleError("The default dist folder must not redirect outside the repository.")
        destination = folder / f"wanda-demo-{commit[:12]}.zip"
    else:
        destination = Path(output).expanduser().absolute()
    if destination.suffix.lower() != ".zip":
        raise BundleError("Choose a .zip output filename.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = destination.open("xb")
    except FileExistsError:
        raise BundleError("Output already exists. Choose a new --output filename; nothing was overwritten.") from None
    try:
        with handle, zipfile.ZipFile(handle, "w", compression=zipfile.ZIP_STORED) as archive:
            # Stored entries avoid compressor/version differences as well as
            # timestamps, platform modes, source mtimes and filesystem order.
            for name, (data, mode) in sorted(files.items()):
                entry = zipfile.ZipInfo(f"{ARCHIVE_ROOT}/{name}", date_time=_FIXED_TIME)
                entry.create_system = 3  # Unix metadata preserves launcher execute bits.
                entry.external_attr = mode << 16
                entry.compress_type = zipfile.ZIP_STORED
                archive.writestr(entry, data)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    with destination.open("rb") as handle:
        checksum = hashlib.file_digest(handle, "sha256").hexdigest()
    return {"archive": str(destination), "commit": commit, "sha256": checksum, "files": len(files)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build a committed Wanda demo ZIP. Python 3.11+ is still required to run it.")
    parser.add_argument("--ref", default="HEAD", help="Committed Git revision (default: HEAD; excludes workspace edits)")
    parser.add_argument("--output", type=Path, help="New ZIP filename; explicitly allows a location outside dist")
    args = parser.parse_args(argv)
    try:
        result = build_bundle(ref=args.ref, output=args.output)
    except BundleError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, UnicodeError):
        print("Demo bundle was not created. Check Git, the committed revision, launcher permissions and a new .zip output path.", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    print("Unzip and open START_HERE.txt. Python 3.11+ must already be installed; Git is not needed to run Wanda.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
