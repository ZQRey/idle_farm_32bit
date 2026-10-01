"""
Desktop Idle Farm - Main Entry Point
A pixel-art idle farming game that lives on your Windows desktop.
"""
import sys
import os
import ctypes
import logging
import traceback

# Ensure we can find our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.app import Application
from src.core.logger import setup_logging


def main():
    """Main entry point for Desktop Idle Farm."""
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("=" * 60)
    logger.info("Desktop Idle Farm starting...")
    logger.info("=" * 60)

    try:
        # Set DPI awareness for proper scaling
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        app = Application()
        app.run()

    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        logger.critical(traceback.format_exc())

        # Try to show error dialog
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Desktop Idle Farm encountered a fatal error:\n\n{e}\n\nCheck logs/game.log for details.",
                "Desktop Idle Farm - Error",
                0x10  # MB_ICONERROR
            )
        except Exception:
            pass

        sys.exit(1)
    finally:
        logger.info("Desktop Idle Farm shutdown complete.")


if __name__ == "__main__":
    main()
