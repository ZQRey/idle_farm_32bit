"""
Pixel-art rendering engine using Pygame.
Handles sprite loading, animation, parallax layers, and day/night cycle.
"""
import os
import logging
import math
from typing import Dict, List, Optional, Tuple

import pygame

from src.core.constants import TILE_SIZE, Colors, ASSETS_DIR

logger = logging.getLogger("renderer")

# Magenta color key for transparency
COLORKEY = (255, 0, 255)


class SpriteSheet:
    """Manages a sprite sheet with named animations."""

    def __init__(self, frames: List[pygame.Surface], frame_duration: float = 0.15):
        self.frames = frames
        self.frame_duration = frame_duration
        self.current_frame = 0
        self.timer = 0.0

    def update(self, dt: float):
        """Update animation."""
        self.timer += dt
        if self.timer >= self.frame_duration:
            self.timer -= self.frame_duration
            self.current_frame = (self.current_frame + 1) % len(self.frames)

    @property
    def image(self) -> pygame.Surface:
        return self.frames[self.current_frame]


class AssetManager:
    """Loads and caches all game sprites."""

    def __init__(self):
        self._cache: Dict[str, pygame.Surface] = {}
        self._animations: Dict[str, SpriteSheet] = {}

    def load_sprite(self, path: str) -> Optional[pygame.Surface]:
        """Load a single sprite. Path relative to assets dir."""
        if path in self._cache:
            return self._cache[path]

        full_path = os.path.join(ASSETS_DIR, path)
        if not os.path.exists(full_path):
            logger.warning(f"Sprite not found: {full_path}")
            return None

        try:
            surface = pygame.image.load(full_path)
            if surface.get_alpha() is not None:
                surface = surface.convert_alpha()
            else:
                surface = surface.convert()
                surface.set_colorkey(COLORKEY)
            self._cache[path] = surface
            return surface
        except Exception as e:
            logger.error(f"Failed to load sprite {full_path}: {e}")
            return None

    def load_animation(self, folder: str, prefix: str,
                       frame_count: int, frame_duration: float = 0.15) -> Optional[SpriteSheet]:
        """Load animation frames. E.g., load_animation('tractors/small', 'right', 4)"""
        key = f"{folder}/{prefix}"
        if key in self._animations:
            return self._animations[key]

        frames = []
        for i in range(frame_count):
            path = f"{folder}/{prefix}_{i}.png"
            sprite = self.load_sprite(path)
            if sprite:
                frames.append(sprite)

        if frames:
            sheet = SpriteSheet(frames, frame_duration)
            self._animations[key] = sheet
            return sheet
        return None

    def get_sprite(self, path: str) -> Optional[pygame.Surface]:
        """Get cached sprite or load if needed."""
        return self.load_sprite(path)

    def preload_all(self):
        """Preload all assets from the assets directory."""
        count = 0
        for root, dirs, files in os.walk(ASSETS_DIR):
            for f in files:
                if f.endswith('.png'):
                    rel = os.path.relpath(os.path.join(root, f), ASSETS_DIR)
                    rel = rel.replace('\\', '/')
                    self.load_sprite(rel)
                    count += 1
        logger.info(f"Preloaded {count} sprites")


class ParallaxLayer:
    """A single parallax scrolling layer."""

    def __init__(self, color: Tuple[int, ...], y: int, height: int,
                 scroll_speed: float = 0.0):
        self.color = color
        self.y = y
        self.height = height
        self.scroll_speed = scroll_speed
        self.offset_x = 0.0
        self.elements: List[Tuple[pygame.Surface, int, int]] = []

    def add_element(self, surface: pygame.Surface, x: int, y_offset: int):
        """Add a decorative element to this layer."""
        self.elements.append((surface, x, y_offset))

    def update(self, dt: float):
        """Update parallax scroll."""
        if self.scroll_speed != 0:
            self.offset_x = (self.offset_x + self.scroll_speed * dt) % 100

    def draw(self, screen: pygame.Surface, screen_width: int):
        """Draw this layer."""
        pygame.draw.rect(screen, self.color, (0, self.y, screen_width, self.height))
        for surface, x, y_offset in self.elements:
            screen.blit(surface, (x - int(self.offset_x), self.y + y_offset))


class DayNightCycle:
    """Manages the day/night visual overlay."""

    def __init__(self, cycle_seconds: float = 2400):
        self.cycle_seconds = cycle_seconds  # 40 minutes default
        self.time_of_day = 0.3  # Start at morning (0=midnight, 0.5=noon)
        self._overlay = None
        self._last_phase = None

    def update(self, dt: float):
        """Update time of day."""
        self.time_of_day = (self.time_of_day + dt / self.cycle_seconds) % 1.0

    @property
    def phase(self) -> str:
        """Get current phase name."""
        t = self.time_of_day
        if t < 0.2:
            return "night"
        elif t < 0.3:
            return "dawn"
        elif t < 0.45:
            return "morning"
        elif t < 0.7:
            return "day"
        elif t < 0.8:
            return "evening"
        else:
            return "night"

    @property
    def brightness(self) -> float:
        """Get brightness factor (0=dark, 1=bright)."""
        t = self.time_of_day
        if t < 0.2:
            return 0.3
        elif t < 0.3:
            return 0.3 + (t - 0.2) / 0.1 * 0.7
        elif t < 0.7:
            return 1.0
        elif t < 0.8:
            return 1.0 - (t - 0.7) / 0.1 * 0.7
        else:
            return 0.3

    def get_overlay(self, width: int, height: int) -> Optional[pygame.Surface]:
        """Get the day/night tint overlay surface."""
        phase = self.phase
        if phase == "day":
            return None

        if self._overlay is None or self._overlay.get_size() != (width, height):
            self._overlay = pygame.Surface((width, height), pygame.SRCALPHA)

        self._overlay.fill((0, 0, 0, 0))

        if phase == "night":
            alpha = 120
            self._overlay.fill((20, 24, 46, alpha))
        elif phase == "dawn":
            t = (self.time_of_day - 0.2) / 0.1
            alpha = int(120 * (1 - t))
            self._overlay.fill((255, 183, 120, int(40 * (1 - t))))
        elif phase == "morning":
            pass  # No overlay needed
        elif phase == "evening":
            t = (self.time_of_day - 0.7) / 0.1
            alpha = int(60 * t)
            self._overlay.fill((200, 120, 80, alpha))

        return self._overlay

    @property
    def is_night(self) -> bool:
        return self.phase == "night"

    @property
    def show_stars(self) -> bool:
        return self.time_of_day < 0.2 or self.time_of_day > 0.82

    @property
    def show_lights(self) -> bool:
        return self.time_of_day < 0.25 or self.time_of_day > 0.75


class Renderer:
    """Main rendering engine."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.assets = AssetManager()
        self.day_night = DayNightCycle()
        self.camera_x = 0
        self.camera_y = 0
        self._stars: List[Tuple[int, int, int]] = []  # (x, y, brightness)

        # Generate star positions
        import random
        for _ in range(30):
            self._stars.append((
                random.randint(0, max(width, 1920)),
                random.randint(0, 35),
                random.randint(150, 255)
            ))

    def draw_sky(self, screen: pygame.Surface, sky_height: int = 35):
        """Draw the sky background based on time of day."""
        phase = self.day_night.phase
        t = self.day_night.time_of_day

        if phase == "night":
            color = Colors.SKY_NIGHT
        elif phase == "dawn":
            blend = (t - 0.2) / 0.1
            color = self._lerp_color(Colors.SKY_NIGHT, Colors.SKY_DAWN, blend)
        elif phase == "morning":
            blend = (t - 0.3) / 0.15
            color = self._lerp_color(Colors.SKY_DAWN, Colors.SKY_DAY, blend)
        elif phase == "day":
            color = Colors.SKY_DAY
        elif phase == "evening":
            blend = (t - 0.7) / 0.1
            color = self._lerp_color(Colors.SKY_DAY, Colors.SKY_EVENING, blend)
        else:
            blend = min((t - 0.8) / 0.1, 1.0)
            color = self._lerp_color(Colors.SKY_EVENING, Colors.SKY_NIGHT, blend)

        pygame.draw.rect(screen, color, (0, 0, self.width, sky_height))

        # Stars at night
        if self.day_night.show_stars:
            for sx, sy, brightness in self._stars:
                if sx < self.width:
                    twinkle = int(brightness * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.003 + sx)))
                    c = max(0, min(255, twinkle))
                    screen.set_at((sx % self.width, sy % sky_height), (c, c, int(c * 0.9)))

    def draw_day_night_overlay(self, screen: pygame.Surface):
        """Apply day/night tint overlay."""
        overlay = self.day_night.get_overlay(self.width, self.height)
        if overlay:
            screen.blit(overlay, (0, 0))

    @staticmethod
    def _lerp_color(c1, c2, t):
        """Linear interpolate between two colors."""
        t = max(0.0, min(1.0, t))
        return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
