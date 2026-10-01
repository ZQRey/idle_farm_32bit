"""
System Tray integration for Desktop Idle Farm.
Uses pystray for Windows system tray icon and menu.
"""
import logging
import threading
import os
from typing import Callable, Optional

from PIL import Image

logger = logging.getLogger("tray")


class TrayManager:
    """Manages the system tray icon and menu."""

    def __init__(self, icon_path: str, callbacks: dict):
        """
        callbacks should contain:
            on_show_status, on_pause, on_resume, on_hide, on_show,
            on_exit, on_restart, on_settings, on_shop,
            on_workers, on_hire, on_vehicles, on_buy_vehicle,
            on_farm_status, on_fields, on_storage, on_finances,
            on_statistics, on_debug, get_paused, get_hidden
        """
        self.callbacks = callbacks
        self.icon_path = icon_path
        self._tray = None
        self._thread = None
        self._running = False

    def start(self):
        """Start the tray icon in a background thread."""
        import pystray
        from pystray import MenuItem as Item, Menu

        try:
            # Load icon
            if os.path.exists(self.icon_path):
                icon_image = Image.open(self.icon_path)
            else:
                # Fallback: create a simple icon
                icon_image = Image.new('RGB', (16, 16), (60, 130, 50))
                logger.warning(f"Tray icon not found: {self.icon_path}")

            def _get_paused():
                fn = self.callbacks.get('get_paused')
                return fn() if fn else False

            def _get_hidden():
                fn = self.callbacks.get('get_hidden')
                return fn() if fn else False

            def _cb(name):
                fn = self.callbacks.get(name)
                if fn:
                    try:
                        fn()
                    except Exception as e:
                        logger.error(f"Tray callback error ({name}): {e}")

            menu = Menu(
                Item('Desktop Idle Farm', None, enabled=False),
                Menu.SEPARATOR,
                Item('Farm', Menu(
                    Item('Farm Status', lambda: _cb('on_farm_status')),
                    Item('Fields', lambda: _cb('on_fields')),
                    Item('Storage', lambda: _cb('on_storage')),
                    Item('Finances', lambda: _cb('on_finances')),
                )),
                Item('Staff', Menu(
                    Item('Workers', lambda: _cb('on_workers')),
                    Item('Hire Worker', lambda: _cb('on_hire')),
                )),
                Item('Vehicles', Menu(
                    Item('All Vehicles', lambda: _cb('on_vehicles')),
                    Item('Buy Vehicle', lambda: _cb('on_buy_vehicle')),
                )),
                Item('Shop', lambda: _cb('on_shop')),
                Item('Statistics', lambda: _cb('on_statistics')),
                Menu.SEPARATOR,
                Item('Settings', lambda: _cb('on_settings')),
                Menu.SEPARATOR,
                Item(
                    lambda text: 'Resume' if _get_paused() else 'Pause',
                    lambda: _cb('on_resume') if _get_paused() else _cb('on_pause'),
                ),
                Item(
                    lambda text: 'Show Farm' if _get_hidden() else 'Hide Farm',
                    lambda: _cb('on_show') if _get_hidden() else _cb('on_hide'),
                ),
                Item('Restart Scene', lambda: _cb('on_restart')),
                Menu.SEPARATOR,
                Item('Exit', lambda: _cb('on_exit')),
            )

            self._tray = pystray.Icon(
                "desktop_idle_farm",
                icon_image,
                "Desktop Idle Farm",
                menu
            )

            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            logger.info("Tray icon started")

        except Exception as e:
            logger.error(f"Failed to create tray icon: {e}")

    def _run(self):
        """Run the tray icon (blocking, runs in thread)."""
        try:
            self._tray.run()
        except Exception as e:
            logger.error(f"Tray run error: {e}")
        finally:
            self._running = False

    def stop(self):
        """Stop the tray icon."""
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        self._running = False
        logger.info("Tray icon stopped")

    def update_tooltip(self, text: str):
        """Update tray icon tooltip."""
        if self._tray:
            try:
                self._tray.title = text
            except Exception:
                pass

    @property
    def is_running(self) -> bool:
        return self._running
