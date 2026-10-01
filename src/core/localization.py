"""
Localization system for Desktop Idle Farm.
"""
import json
import logging
import os
from typing import Optional

from src.core.constants import LOCALIZATION_DIR

logger = logging.getLogger("i18n")


class Localization:
    """Manages game text translations."""

    def __init__(self, language: str = "en"):
        self._strings = {}
        self._language = language
        self._fallback = {}
        self.load("en")  # Always load English as fallback
        self._fallback = dict(self._strings)
        if language != "en":
            self.load(language)

    def load(self, language: str):
        """Load language file."""
        path = os.path.join(LOCALIZATION_DIR, f"{language}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._strings = json.load(f)
                self._language = language
                logger.info(f"Loaded language: {language}")
            except Exception as e:
                logger.error(f"Failed to load language {language}: {e}")
        else:
            logger.warning(f"Language file not found: {path}")

    def get(self, key: str, **kwargs) -> str:
        """Get localized string. Supports format kwargs."""
        text = self._strings.get(key, self._fallback.get(key, key))
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError):
                pass
        return text

    def t(self, key: str, **kwargs) -> str:
        """Alias for get()."""
        return self.get(key, **kwargs)

    @property
    def language(self) -> str:
        return self._language
