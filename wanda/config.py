"""Configuration comes from the environment or a private file outside Git."""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent


def private_path(value):
    path = Path(value).expanduser().resolve()
    if path == ROOT or ROOT in path.parents:
        raise ValueError("Private configuration and data must be outside the Wanda checkout.")
    return path


def default_data_dir():
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "Wanda"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Wanda"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "wanda"


@dataclass(frozen=True)
class Config:
    data_dir: Path
    port: int = 8765
    voice_enabled: bool = False
    api_key: str = field(default="", repr=False)
    voice_model: str = "gpt-realtime-2.1"
    home_mode: str = "mock"
    home_url: str = field(default="", repr=False)
    home_token: str = field(default="", repr=False)
    home_entities: tuple = field(default=(), repr=False)
    home_allow_insecure_http: bool = False

    @classmethod
    def load(cls, environ=None):
        env = os.environ if environ is None else environ
        raw = {}
        suggested = private_path(env.get("WANDA_DATA_DIR", str(default_data_dir()))) / "config.json"
        # Explicit empty WANDA_CONFIG disables file loading (useful for isolated tests).
        selected = env.get("WANDA_CONFIG") if "WANDA_CONFIG" in env else str(suggested) if suggested.is_file() else None
        if selected:
            path = private_path(selected)
            if path.stat().st_size > 16384:
                raise ValueError("Private configuration is too large.")
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Private configuration must be a JSON object.")

        def value(name, default=""):
            return env.get(name, raw.get(name, default))

        data_dir = private_path(value("WANDA_DATA_DIR", str(default_data_dir())))
        port = int(value("WANDA_PORT", 8765))
        if not 1024 <= port <= 65535:
            raise ValueError("WANDA_PORT must be between 1024 and 65535.")
        home_mode = value("WANDA_HOME_MODE", "mock")
        if home_mode not in ("mock", "homeassistant"):
            raise ValueError("WANDA_HOME_MODE must be mock or homeassistant.")
        entities = value("WANDA_HOME_ENTITIES", "")
        if isinstance(entities, str):
            entities = tuple(x.strip() for x in entities.split(",") if x.strip())
        if not isinstance(entities, (tuple, list)) or any(not isinstance(x, str) for x in entities):
            raise ValueError("WANDA_HOME_ENTITIES must list approved light entity IDs.")
        key = value("OPENAI_API_KEY")
        token = value("HOME_ASSISTANT_TOKEN")
        if any(not isinstance(x, str) for x in (key, token, value("WANDA_VOICE_MODEL", "gpt-realtime-2.1"))):
            raise ValueError("Credentials and model must be text.")
        return cls(
            data_dir=data_dir, port=port,
            voice_enabled=str(value("WANDA_ENABLE_CLOUD_VOICE", "false")).lower() == "true",
            api_key=key, voice_model=value("WANDA_VOICE_MODEL", "gpt-realtime-2.1"),
            home_mode=home_mode, home_url=value("HOME_ASSISTANT_URL"),
            home_token=token, home_entities=tuple(entities),
            home_allow_insecure_http=str(value("WANDA_HA_ALLOW_INSECURE_HTTP", "false")).lower() == "true",
        )

    def prepare(self):
        private_path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.data_dir.is_symlink():
            raise ValueError("Private data directory must not be a symlink.")
        if os.name != "nt":
            self.data_dir.chmod(0o700)
