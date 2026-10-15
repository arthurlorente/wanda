"""python -m wanda: start, open, diagnose and stop the local application."""

import argparse
import getpass
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import webbrowser

from .config import Config, stop_data_dir


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def local_opener():
    # A stale port must never redirect the launcher capability elsewhere.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def state_file(config):
    return config.data_dir / "launcher.json"


def read_running(config):
    try:
        state = json.loads(state_file(config).read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            return None
        port = state["port"]
        token = state["token"]
        if type(port) is not int or not 1024 <= port <= 65535 or not isinstance(token, str) or not token:
            return None
        request = urllib.request.Request(f"http://127.0.0.1:{port}/api/status", headers={"Authorization": "Bearer " + token})
        # Never use environment proxy settings for a local capability.
        with local_opener().open(request, timeout=2) as response:
            status = json.loads(response.read(16384))
        return state if isinstance(status, dict) and status.get("version") and status.get("mode") == "demo" else None
    except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError):
        return None


def open_browser(state):
    webbrowser.open(f"http://127.0.0.1:{state['port']}/#token={state['token']}")


def save_state(config, state):
    fd, temp = tempfile.mkstemp(prefix=".launch-", dir=config.data_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        os.replace(temp, state_file(config))
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def stop(config):
    try:
        state_file(config).lstat()
    except FileNotFoundError:
        print("Wanda is already stopped, or this data folder has no active Wanda session.")
        return 0
    except OSError:
        print("Wanda cannot verify or stop this local session because its launcher state is unreadable. "
              "If its window is open, press Control+C there.", file=sys.stderr)
        return 1
    state = read_running(config)
    if not state:
        print("Wanda cannot verify or stop this local session because its saved launcher state is invalid "
              "or the service is unreachable. If its window is open, press Control+C there.", file=sys.stderr)
        return 1
    request = urllib.request.Request(f"http://127.0.0.1:{state['port']}/api/shutdown", data=b"{}", method="POST",
                                     headers={"Authorization": "Bearer " + state["token"], "Content-Type": "application/json"})
    with local_opener().open(request, timeout=3):
        pass
    print("Wanda is stopping. Saved memories remain on this computer.")
    return 0


def configure_voice(config):
    if not sys.stdin.isatty():
        print("Open Configure Voice in a terminal to enter a private key securely.")
        return 1
    print("Optional cloud voice setup. No provider request is made by this setup.")
    print("Review docs/PROVIDERS.md first. Cloud audio leaves this computer and API charges may apply.")
    print("You still need to consent in the browser before each microphone session.")
    choice = input("Configure your own OpenAI API key now? Type yes, disable, or press Return to cancel: ").strip().lower()
    if choice not in ("yes", "disable"):
        print("Nothing changed.")
        return 0
    from .config import private_path
    config.prepare()
    path = private_path(os.environ.get("WANDA_CONFIG") or config.data_dir / "config.json")
    if path.is_symlink():
        raise ValueError("Private config must not be a symlink.")
    current = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    if not isinstance(current, dict):
        raise ValueError("Invalid configuration.")
    if choice == "yes":
        key = getpass.getpass("Paste your API key (hidden; kept only on this computer): ").strip()
        if not key or any(char in key for char in "\r\n"):
            print("No valid key entered. Nothing changed.")
            return 1
        current.update({"OPENAI_API_KEY": key, "WANDA_ENABLE_CLOUD_VOICE": True})
    else:
        current.update({"OPENAI_API_KEY": "", "WANDA_ENABLE_CLOUD_VOICE": False})
    fd, temp = tempfile.mkstemp(prefix=".config-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(current, handle, indent=2)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    print("Private configuration saved. Stop Wanda, then Start Wanda to apply it.")
    print("No model access, billing, privacy settings or live audio have been verified.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Start Wanda's private local V0 demo.")
    parser.add_argument("--no-browser", action="store_true", help="Start without opening a browser")
    parser.add_argument("--stop", action="store_true", help="Stop this local Wanda service")
    parser.add_argument("--doctor", action="store_true", help="Check runtime and configuration without connecting to services")
    parser.add_argument("--configure-voice", action="store_true", help="Optional private API key setup; no provider calls")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        print("Wanda needs Python 3.11 or newer. See docs/MORNING_HANDOFF.md.", file=sys.stderr)
        return 1
    if args.stop:
        try:
            data_dir = stop_data_dir()
        except (ValueError, OSError, TypeError):
            print("Wanda could not identify the data folder for Stop Wanda. Set WANDA_DATA_DIR "
                  "to the folder used at startup, or repair the selected WANDA_CONFIG file; "
                  "no other folders were searched.", file=sys.stderr)
            return 1
        try:
            return stop(Config(data_dir=data_dir))
        except (ValueError, OSError, TypeError):
            print("Wanda could not stop the selected local session. Check its launcher window "
                  "and try Stop Wanda again.", file=sys.stderr)
            return 1
    try:
        config = Config.load()
        if args.configure_voice:
            return configure_voice(config)
        if args.doctor:
            import sqlite3
            from .home import HomeAssistantAdapter
            from .voice import VoiceProvider
            VoiceProvider(config.api_key, config.voice_model)
            if config.home_mode == "homeassistant":
                HomeAssistantAdapter(config.home_url, config.home_token, config.home_entities,
                                     allow_insecure_http=config.home_allow_insecure_http)
            print(f"Python {sys.version_info.major}.{sys.version_info.minor}: ready")
            print(f"SQLite {sqlite3.sqlite_version}: ready")
            print("Runtime packages: none required")
            print("Cloud voice: " + ("configured, live validation still required" if config.voice_enabled and config.api_key else "off; local demo needs no key"))
            print("Home: " + config.home_mode)
            print("Configuration: valid; no provider or home connection attempted")
            return 0
        config.prepare()
        running = read_running(config)
        if running:
            if not args.no_browser:
                open_browser(running)
            print("Wanda is already running. Use Stop Wanda when finished.")
            return 0
        from .server import Application, LocalServer
        app = Application(config)
        try:
            server = LocalServer(app)
        except OSError:
            app.close()
            print("Wanda could not open its local port. Another app may be using it. Set WANDA_PORT to a free port (for example 8766).", file=sys.stderr)
            return 1
        state = {"port": server.server_address[1], "token": app.token, "pid": os.getpid()}
        save_state(config, state)
        if not args.no_browser:
            threading.Timer(0.5, open_browser, args=(state,)).start()
        print(f"Wanda is ready at http://127.0.0.1:{state['port']}", flush=True)
        print("This window keeps Wanda running. Press Control+C or use Stop Wanda to stop.", flush=True)
        print("Demo chat is scripted. Memory is local. Home devices are " + ("simulated." if config.home_mode == "mock" else "configured for real use; review permissions before acting."), flush=True)

        def shutdown(*_):
            threading.Thread(target=server.shutdown, daemon=True).start()

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)
        try:
            server.serve_forever(poll_interval=0.2)
        finally:
            server.server_close()
            app.close()
            try:
                current = json.loads(state_file(config).read_text(encoding="utf-8"))
                if isinstance(current, dict) and current.get("token") == state["token"]:
                    state_file(config).unlink()
            except (OSError, ValueError):
                pass
        return 0
    except (ValueError, OSError, TypeError):
        print("Wanda could not read its private configuration or create its data folder. Check the example config and folder permissions; no credentials were printed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
