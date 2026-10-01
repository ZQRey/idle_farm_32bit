"""
Main Application class for Desktop Idle Farm.
Manages the game loop, window, tray, and all subsystems.
"""
import logging
import os
import sys
import time
import ctypes
import threading
from typing import Optional

import pygame

from src.core.constants import (
    VERSION, GAME_TITLE, DEFAULT_FPS, ASSETS_DIR,
    AUTOSAVE_INTERVAL_SECONDS, DAY_CYCLE_SECONDS,
    SIMULATION_TICK_INTERVAL, MAX_OFFLINE_HOURS
)
from src.core.windows_integration import (
    setup_game_window, set_click_through, set_window_bottom,
    calculate_window_rect, is_fullscreen_app_running, get_screen_info
)
from src.config.game_config import GameConfig
from src.core.localization import Localization
from src.simulation.engine import SimulationEngine
from src.world.game_world import GameWorld
from src.rendering.sprite_generator import generate_all_sprites
from src.tray.tray_manager import TrayManager
from src.persistence.save_manager import SaveManager

logger = logging.getLogger("app")


class Application:
    """
    Main application class. Manages:
    - Pygame window with desktop integration
    - System tray
    - Game simulation
    - Rendering
    - Save/Load
    """

    def __init__(self):
        self.config = GameConfig()
        self.i18n = Localization(self.config.language)
        self.save_manager = SaveManager()
        self.simulation = SimulationEngine()

        # State
        self.running = False
        self.paused = False
        self.hidden = False
        self.click_through = self.config.click_through

        # Window
        self.screen: Optional[pygame.Surface] = None
        self.hwnd = 0
        self.window_x = 0
        self.window_y = 0
        self.window_width = 0
        self.window_height = 0

        # Game world
        self.world: Optional[GameWorld] = None

        # Tray
        self.tray: Optional[TrayManager] = None

        # Timing
        self.fps = self.config.fps
        self.clock = None
        self.autosave_timer = 0.0

        # Thread safety
        self._lock = threading.Lock()

    def run(self):
        """Main entry point - initialize and start game loop."""
        logger.info(f"Desktop Idle Farm v{VERSION}")
        logger.info(f"Python {sys.version}")

        # Generate sprites if needed
        self._ensure_assets()

        # Initialize Pygame
        self._init_pygame()

        # Setup Windows desktop integration
        self._setup_desktop_window()

        # Initialize game world
        self._init_game()

        # Start system tray
        self._start_tray()

        # Main game loop
        self._game_loop()

        # Cleanup
        self._shutdown()

    def _ensure_assets(self):
        """Generate game assets if they don't exist."""
        marker = os.path.join(ASSETS_DIR, ".generated")
        if not os.path.exists(marker):
            logger.info("Generating game assets...")
            count = generate_all_sprites(ASSETS_DIR)
            # Write marker
            with open(marker, 'w') as f:
                f.write(f"Generated {count} sprites at {time.time()}")
            logger.info(f"Asset generation complete: {count} sprites")
        else:
            logger.info("Assets already exist, skipping generation")

    def _init_pygame(self):
        """Initialize Pygame with proper settings."""
        # Initialize only needed subsystems
        pygame.display.init()
        pygame.font.init()
        # Don't init audio for now to save resources
        # pygame.mixer.init()

        # Calculate window position
        scene_height = self.config.scene_height
        x, y, w, h, screen_info = calculate_window_rect(scene_height)
        self.window_x = x
        self.window_y = y
        self.window_width = w
        self.window_height = h

        # Create frameless window
        os.environ['SDL_VIDEO_WINDOW_POS'] = f'{x},{y}'

        self.screen = pygame.display.set_mode(
            (w, h),
            pygame.NOFRAME | pygame.HWSURFACE | pygame.DOUBLEBUF
        )
        pygame.display.set_caption(GAME_TITLE)

        self.clock = pygame.time.Clock()

        logger.info(f"Pygame initialized: {w}x{h} at ({x},{y})")

    def _setup_desktop_window(self):
        """Configure the window for desktop integration."""
        # Get the window handle
        info = pygame.display.get_wm_info()
        self.hwnd = info.get('window', 0)

        if self.hwnd:
            logger.info(f"Window handle: {self.hwnd}")
            setup_game_window(
                self.hwnd,
                self.config.scene_height,
                self.click_through
            )
            # Push to bottom of Z-order
            set_window_bottom(self.hwnd)
        else:
            logger.error("Could not get window handle!")

    def _init_game(self):
        """Initialize or load the game world."""
        self.world = GameWorld(self.window_width, self.window_height)

        # Try to load save
        save_data = self.save_manager.load()
        if save_data:
            try:
                self.world.load_from_dict(save_data)
                logger.info("Game loaded from save")

                # Calculate offline progress
                offline_time = self.save_manager.get_offline_time()
                if offline_time > 60:  # More than 1 minute
                    max_offline = self.config.get(
                        'gameplay.max_offline_hours', MAX_OFFLINE_HOURS) * 3600
                    offline_time = min(offline_time, max_offline)
                    logger.info(f"Offline time: {offline_time:.0f}s")
                    self.simulation.simulate_offline(offline_time)
                    # TODO: Show offline progress summary

            except Exception as e:
                logger.error(f"Failed to load save: {e}")
                self.world.setup_new_game()
        else:
            self.world.setup_new_game()

        # Preload assets
        self.world.renderer.assets.preload_all()

        # Register simulation callbacks
        self.simulation.register_tick(self._simulation_tick)

    def _simulation_tick(self, dt: float):
        """Called for each simulation tick."""
        if self.world:
            self.world.update(dt)

    def _start_tray(self):
        """Start the system tray icon."""
        icon_path = os.path.join(ASSETS_DIR, 'ui', 'tray_icon.png')

        callbacks = {
            'on_farm_status': self._on_farm_status,
            'on_fields': self._on_fields,
            'on_storage': self._on_storage,
            'on_finances': self._on_finances,
            'on_workers': self._on_workers,
            'on_hire': self._on_hire_worker,
            'on_vehicles': self._on_vehicles,
            'on_buy_vehicle': self._on_buy_vehicle,
            'on_shop': self._on_shop,
            'on_statistics': self._on_statistics,
            'on_settings': self._on_settings,
            'on_pause': self._on_pause,
            'on_resume': self._on_resume,
            'on_hide': self._on_hide,
            'on_show': self._on_show,
            'on_restart': self._on_restart,
            'on_exit': self._on_exit,
            'get_paused': lambda: self.paused,
            'get_hidden': lambda: self.hidden,
        }

        self.tray = TrayManager(icon_path, callbacks)
        self.tray.start()

    def _game_loop(self):
        """Main game loop."""
        self.running = True
        logger.info("Entering main game loop")

        while self.running:
            dt = self.clock.tick(self.fps) / 1000.0
            dt = min(dt, 0.1)  # Cap delta time

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            # Simulation update
            if not self.paused:
                self.simulation.update(dt)

            # Keep window at bottom of Z-order
            if self.hwnd and not self.hidden:
                set_window_bottom(self.hwnd)

            # Fullscreen detection
            if self.config.get('display.hide_during_fullscreen', True):
                if is_fullscreen_app_running():
                    if not self.hidden:
                        self.hidden = True
                else:
                    # Don't auto-show if user manually hid
                    pass

            # Render
            if not self.hidden and self.world:
                self.world.draw(self.screen)
                pygame.display.flip()

            # Autosave
            self.autosave_timer += dt
            if self.autosave_timer >= AUTOSAVE_INTERVAL_SECONDS:
                self.autosave_timer = 0
                self._autosave()

            # Update tray tooltip
            if self.tray and self.world:
                money = self.world.economy.money
                self.tray.update_tooltip(
                    f"Desktop Idle Farm | ${money:.0f}"
                )

    def _autosave(self):
        """Perform autosave."""
        if self.world:
            try:
                state = self.world.to_dict()
                self.save_manager.save(state)
            except Exception as e:
                logger.error(f"Autosave failed: {e}")

    def _shutdown(self):
        """Clean shutdown."""
        logger.info("Shutting down...")

        # Save game
        if self.world:
            try:
                state = self.world.to_dict()
                self.save_manager.save(state)
                logger.info("Final save completed")
            except Exception as e:
                logger.error(f"Final save failed: {e}")

        # Save config
        self.config.save()

        # Stop tray
        if self.tray:
            self.tray.stop()

        # Quit pygame
        pygame.quit()
        logger.info("Shutdown complete")

    # ========== TRAY CALLBACKS ==========

    def _on_farm_status(self):
        """Show farm status window."""
        if not self.world:
            return
        self._show_info_window("Farm Status",
            f"Farm Level: {self.world.farm_level}\n"
            f"Money: ${self.world.economy.money:.0f}\n"
            f"Fuel: {self.world.economy.fuel:.0f}L\n"
            f"Workers: {len(self.world.workers)}\n"
            f"Vehicles: {len(self.world.vehicles)}\n"
            f"Fields: {len(self.world.fields)}\n"
            f"Weather: {self.world.weather.current.name}\n"
            f"Time: {self.world.renderer.day_night.phase}\n"
            f"Total Harvests: {self.world.total_harvests}\n"
            f"Playtime: {self.world.playtime / 3600:.1f}h"
        )

    def _on_fields(self):
        if not self.world:
            return
        text = ""
        for f in self.world.fields:
            text += (f"Field {f.field_id}: {f.crop_type}\n"
                    f"  Size: {f.width}x{f.height}\n"
                    f"  Growth: {f.average_growth:.0%}\n"
                    f"  Ready: {'Yes' if f.is_ready_for_harvest else 'No'}\n\n")
        self._show_info_window("Fields", text or "No fields")

    def _on_storage(self):
        if not self.world:
            return
        s = self.world.economy.storage
        text = f"Storage: {s.total_stored:.0f}/{s.capacity:.0f} kg ({s.fill_percentage:.0f}%)\n\n"
        for crop, amount in s.contents.items():
            price = self.world.economy.market.current_prices.get(crop, 0)
            text += f"  {crop}: {amount:.0f} kg (${price:.1f}/100kg)\n"
        self._show_info_window("Storage", text)

    def _on_finances(self):
        if not self.world:
            return
        e = self.world.economy
        text = (f"Money: ${e.money:.0f}\n"
                f"Total Earned: ${e.total_earned:.0f}\n"
                f"Total Spent: ${e.total_spent:.0f}\n"
                f"Total Harvested: {e.total_harvested:.0f} kg\n\n"
                f"Market Prices:\n")
        for crop, price in e.market.current_prices.items():
            text += f"  {crop}: ${price:.1f}/100kg\n"
        self._show_info_window("Finances", text)

    def _on_workers(self):
        if not self.world:
            return
        text = ""
        for w in self.world.workers:
            text += (f"{w.name} (Lv.{w.level} {w.profession.name})\n"
                    f"  Energy: {w.energy:.0f}% | Mood: {w.mood:.0f}%\n"
                    f"  Task: {w.current_task.name}\n"
                    f"  Skills: D{w.driving} A{w.agronomy} R{w.repair} H{w.harvesting}\n\n")
        self._show_info_window("Workers", text or "No workers")

    def _on_hire_worker(self):
        if not self.world:
            return
        cost = 200 + len(self.world.workers) * 100
        if self.world.economy.can_afford(cost):
            from src.entities.workers.worker import Profession
            import random
            prof = random.choice(list(Profession))
            w = Worker(prof)
            w.x = self.world.farmhouse_x + 30
            w.y = self.world.ground_y
            self.world.workers.append(w)
            self.world.economy.spend(cost, f"Hired {w.name}")
            self._show_info_window("Hired!",
                f"Hired {w.name}\n"
                f"Profession: {prof.name}\n"
                f"Cost: ${cost}")
        else:
            self._show_info_window("Cannot Hire",
                f"Not enough money. Need: ${cost}")

    def _on_vehicles(self):
        if not self.world:
            return
        text = ""
        for v in self.world.vehicles:
            text += (f"{v.data['name']} (ID:{v.id})\n"
                    f"  State: {v.state.name}\n"
                    f"  Condition: {v.condition:.0f}%\n"
                    f"  Fuel: {v.fuel:.0f}/{v.fuel_capacity:.0f}L\n"
                    f"  Attachment: {v.attachment.name}\n\n")
        self._show_info_window("Vehicles", text or "No vehicles")

    def _on_buy_vehicle(self):
        if not self.world:
            return
        from src.entities.vehicles.vehicle import VEHICLE_DATA, VehicleType
        text = "Available Vehicles:\n\n"
        for vtype, data in VEHICLE_DATA.items():
            text += f"  {data['name']}: ${data['price']}\n"
        # For now, just show the catalog
        # TODO: Implement proper purchase dialog
        self._show_info_window("Buy Vehicle", text)

    def _on_shop(self):
        self._on_buy_vehicle()

    def _on_statistics(self):
        if not self.world:
            return
        text = (f"Playtime: {self.world.playtime / 3600:.1f} hours\n"
                f"Farm Level: {self.world.farm_level}\n"
                f"Total Harvests: {self.world.total_harvests}\n"
                f"Total Earned: ${self.world.economy.total_earned:.0f}\n"
                f"Total Spent: ${self.world.economy.total_spent:.0f}\n"
                f"Total Harvested: {self.world.economy.total_harvested:.0f} kg\n"
                f"Events: {self.world.events.total_events}\n"
                f"Workers: {len(self.world.workers)}\n"
                f"Vehicles: {len(self.world.vehicles)}")
        self._show_info_window("Statistics", text)

    def _on_settings(self):
        text = (f"Scene Height: {self.config.scene_height}px\n"
                f"FPS: {self.config.fps}\n"
                f"Click-through: {self.config.click_through}\n"
                f"Language: {self.config.language}\n\n"
                f"Edit config/settings.json to change settings.")
        self._show_info_window("Settings", text)

    def _on_pause(self):
        self.paused = True
        self.simulation.pause()
        logger.info("Game paused")

    def _on_resume(self):
        self.paused = False
        self.simulation.resume()
        logger.info("Game resumed")

    def _on_hide(self):
        self.hidden = True
        if self.hwnd:
            ctypes.windll.user32.ShowWindow(self.hwnd, 0)  # SW_HIDE
        logger.info("Farm hidden")

    def _on_show(self):
        self.hidden = False
        if self.hwnd:
            ctypes.windll.user32.ShowWindow(self.hwnd, 5)  # SW_SHOW
            set_window_bottom(self.hwnd)
        logger.info("Farm shown")

    def _on_restart(self):
        if self.world:
            self.world.setup_new_game()
        logger.info("Scene restarted")

    def _on_exit(self):
        self.running = False
        logger.info("Exit requested via tray")

    def _show_info_window(self, title: str, text: str):
        """Show a simple info window using tkinter (lightweight)."""
        def _show():
            try:
                import tkinter as tk
                from tkinter import scrolledtext

                root = tk.Tk()
                root.title(f"Desktop Idle Farm - {title}")
                root.geometry("400x350")
                root.configure(bg='#282c34')
                root.attributes('-topmost', True)

                # Title label
                title_label = tk.Label(root, text=title, font=('Segoe UI', 14, 'bold'),
                                      fg='#64b45a', bg='#282c34')
                title_label.pack(pady=(10, 5))

                # Text area
                text_area = scrolledtext.ScrolledText(
                    root, wrap=tk.WORD, font=('Consolas', 10),
                    bg='#373b44', fg='#e6e6eb', insertbackground='white',
                    relief='flat', borderwidth=0, padx=10, pady=10
                )
                text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
                text_area.insert(tk.END, text)
                text_area.configure(state='disabled')

                # Close button
                close_btn = tk.Button(root, text="Close", command=root.destroy,
                                     font=('Segoe UI', 10), bg='#505560',
                                     fg='white', relief='flat', padx=20)
                close_btn.pack(pady=(5, 10))

                root.mainloop()
            except Exception as e:
                logger.error(f"Info window error: {e}")

        # Show in separate thread to not block game
        threading.Thread(target=_show, daemon=True).start()
