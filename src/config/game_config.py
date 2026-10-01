"""
Game configuration management.
Handles loading, saving, and accessing game settings.
"""
import json
import logging
import os
from typing import Any

from src.core.constants import (
    CONFIG_DIR, DEFAULT_FPS, DEFAULT_SCENE_HEIGHT,
    AUTOSAVE_INTERVAL_SECONDS, MAX_OFFLINE_HOURS, VERSION
)

logger = logging.getLogger("config")

DEFAULT_CONFIG = {
    "version": VERSION,
    "display": {
        "scene_height": DEFAULT_SCENE_HEIGHT,
        "fps": DEFAULT_FPS,
        "monitor": 0,
        "low_power_mode": False,
        "hide_during_fullscreen": True,
        "particle_quality": "medium",
    },
    "gameplay": {
        "click_through": True,
        "auto_sell": "never",
        "auto_sell_threshold": 80,
        "auto_sell_min_price": 0,
        "simulation_speed": 1,
        "offline_progress": True,
        "max_offline_hours": MAX_OFFLINE_HOURS,
    },
    "audio": {
        "master_volume": 0.5,
        "machinery_volume": 0.3,
        "nature_volume": 0.4,
        "weather_volume": 0.3,
        "ui_volume": 0.5,
        "music_volume": 0.0,
        "muted": False,
    },
    "save": {
        "autosave_interval": AUTOSAVE_INTERVAL_SECONDS,
    },
    "general": {
        "language": "en",
        "start_with_windows": False,
        "show_notifications": True,
    },
    "debug": {
        "enabled": False,
        "show_fps": False,
        "show_grid": False,
        "show_hitboxes": False,
    },
}


class GameConfig:
    """Manages game configuration."""

    def __init__(self):
        self._config = {}
        self._path = os.path.join(CONFIG_DIR, "settings.json")
        self.load()

    def load(self):
        """Load config from file, creating defaults if needed."""
        os.makedirs(CONFIG_DIR, exist_ok=True)

        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Merge with defaults (keep any new default keys)
                self._config = self._deep_merge(DEFAULT_CONFIG, loaded)
                logger.info(f"Config loaded from {self._path}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                self._config = dict(DEFAULT_CONFIG)
        else:
            self._config = dict(DEFAULT_CONFIG)
            self.save()
            logger.info(f"Created default config at {self._path}")

    def save(self):
        """Save current config to file."""
        os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.debug("Config saved")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get config value by dot-separated path. E.g., 'display.fps'."""
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, key_path: str, value: Any):
        """Set config value by dot-separated path."""
        keys = key_path.split(".")
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value

    @property
    def scene_height(self) -> int:
        return self.get("display.scene_height", DEFAULT_SCENE_HEIGHT)

    @property
    def fps(self) -> int:
        return self.get("display.fps", DEFAULT_FPS)

    @property
    def click_through(self) -> bool:
        return self.get("gameplay.click_through", True)

    @property
    def language(self) -> str:
        return self.get("general.language", "en")

    @property
    def simulation_speed(self) -> int:
        return self.get("gameplay.simulation_speed", 1)

    @staticmethod
    def _deep_merge(default: dict, override: dict) -> dict:
        """Deep merge override into default, preserving all default keys."""
        result = dict(default)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = GameConfig._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
