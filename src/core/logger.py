"""
Logging configuration for Desktop Idle Farm.
Handles log rotation, formatting, and multiple output targets.
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime


def setup_logging(log_dir: str = "logs", level: int = logging.DEBUG):
    """Set up logging with file rotation and console output."""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "game.log")

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)

    # Clear any existing handlers
    root.handlers.clear()

    # File handler with rotation (5 MB max, keep 3 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)-25s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_fmt)
    root.addHandler(file_handler)

    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        "[%(levelname)-7s] %(name)-20s: %(message)s"
    )
    console_handler.setFormatter(console_fmt)
    root.addHandler(console_handler)

    # Suppress noisy loggers
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('PIL.PngImagePlugin').setLevel(logging.WARNING)
    logging.getLogger('PIL.Image').setLevel(logging.WARNING)

    logging.info(f"Logging initialized. Log file: {os.path.abspath(log_file)}")
    logging.info(f"Session started: {datetime.now().isoformat()}")
