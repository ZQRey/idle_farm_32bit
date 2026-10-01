"""
Save/Load persistence system.
Implements atomic saves with backup and recovery.
"""
import json
import logging
import os
import shutil
import time
from typing import Optional, Dict, Any

from src.core.constants import SAVES_DIR, VERSION

logger = logging.getLogger("persistence")

SAVE_FILE = "farm_save.json"
BACKUP_FILE = "farm_save.backup.json"
RECOVERY_FILE = "farm_save.recovery.json"


class SaveManager:
    """Manages game state persistence with atomic saves and backups."""

    def __init__(self, save_dir: str = SAVES_DIR):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        self.save_path = os.path.join(save_dir, SAVE_FILE)
        self.backup_path = os.path.join(save_dir, BACKUP_FILE)
        self.recovery_path = os.path.join(save_dir, RECOVERY_FILE)
        self.last_save_time = 0.0

    def save(self, game_state: dict) -> bool:
        """Save game state with atomic write and backup."""
        try:
            # Add metadata
            save_data = {
                "saveVersion": 1,
                "gameVersion": VERSION,
                "timestamp": time.time(),
                "playtime": game_state.get('playtime', 0),
                **game_state,
            }

            # Backup existing save
            if os.path.exists(self.save_path):
                try:
                    shutil.copy2(self.save_path, self.backup_path)
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")

            # Atomic write: write to temp file, then rename
            temp_path = self.save_path + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

            # Replace original
            if os.path.exists(self.save_path):
                os.replace(temp_path, self.save_path)
            else:
                os.rename(temp_path, self.save_path)

            self.last_save_time = time.time()
            logger.debug("Game saved successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to save game: {e}")
            # Try recovery save
            try:
                with open(self.recovery_path, 'w', encoding='utf-8') as f:
                    json.dump(game_state, f, ensure_ascii=False)
                logger.info("Recovery save created")
            except Exception:
                pass
            return False

    def load(self) -> Optional[dict]:
        """Load game state. Tries main save, then backup, then recovery."""
        # Try main save
        data = self._try_load(self.save_path)
        if data:
            logger.info("Loaded main save")
            return data

        # Try backup
        data = self._try_load(self.backup_path)
        if data:
            logger.warning("Main save corrupted, loaded backup")
            return data

        # Try recovery
        data = self._try_load(self.recovery_path)
        if data:
            logger.warning("Main and backup corrupted, loaded recovery save")
            return data

        logger.info("No save file found, starting new game")
        return None

    def _try_load(self, path: str) -> Optional[dict]:
        """Try to load a save file."""
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Basic validation
            if not isinstance(data, dict):
                return None
            return data
        except Exception as e:
            logger.error(f"Failed to load {path}: {e}")
            return None

    def get_offline_time(self) -> float:
        """Get time since last save (for offline progress)."""
        data = self.load()
        if data and 'timestamp' in data:
            elapsed = time.time() - data['timestamp']
            return max(0, elapsed)
        return 0

    def has_save(self) -> bool:
        """Check if any save file exists."""
        return (os.path.exists(self.save_path) or
                os.path.exists(self.backup_path) or
                os.path.exists(self.recovery_path))
