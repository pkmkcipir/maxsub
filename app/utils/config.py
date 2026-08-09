"""Penyimpanan pengaturan pengguna (persisten antar sesi)."""
import json
import os
import sys


def get_config_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    path = os.path.join(base, "MaxSubtitle")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        path = os.path.expanduser("~")
    return path


class ConfigManager:
    DEFAULTS = {
        "model_size": "small",
        "device": "auto",
        "source_language": "auto",
        "target_language": "id",
        "theme": "dark",
        "window_geometry": "1280x800",
        "burn_in_subtitle": True,
        "last_export_dir": "",
        "last_open_dir": "",
    }

    def __init__(self):
        self.path = os.path.join(get_config_dir(), "config.json")
        self.data = dict(self.DEFAULTS)
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self.data.update(loaded)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def get(self, key, default=None):
        if key in self.data:
            return self.data[key]
        if default is not None:
            return default
        return self.DEFAULTS.get(key)

    def set(self, key, value):
        self.data[key] = value
