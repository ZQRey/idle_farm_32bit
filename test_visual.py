"""
Quick test to run the game and capture a screenshot of the pygame surface.
"""
import sys
import os
import ctypes
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.logger import setup_logging
setup_logging()

# DPI awareness
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

import pygame
from src.core.constants import ASSETS_DIR
from src.core.windows_integration import calculate_window_rect, setup_game_window, set_window_bottom
from src.rendering.sprite_generator import generate_all_sprites
from src.world.game_world import GameWorld

# Generate assets
marker = os.path.join(ASSETS_DIR, ".generated")
if not os.path.exists(marker):
    count = generate_all_sprites(ASSETS_DIR)
    with open(marker, 'w') as f:
        f.write(f"Generated {count}")

# Setup pygame
pygame.display.init()
pygame.font.init()
x, y, w, h, si = calculate_window_rect(180)
os.environ['SDL_VIDEO_WINDOW_POS'] = f'{x},{y}'
screen = pygame.display.set_mode((w, h), pygame.NOFRAME | pygame.HWSURFACE | pygame.DOUBLEBUF)
info = pygame.display.get_wm_info()
hwnd = info.get('window', 0)
if hwnd:
    setup_game_window(hwnd, 180, True)
    set_window_bottom(hwnd)

# Create world
world = GameWorld(w, h)
world.setup_new_game()
world.renderer.assets.preload_all()

# Run frames to let vehicles move to fields and start working
clock = pygame.time.Clock()
for i in range(250):  # ~8 seconds at 30fps
    dt = clock.tick(30) / 1000.0
    for event in pygame.event.get():
        pass
    world.update(dt)
    world.draw(screen)
    pygame.display.flip()
    if hwnd:
        set_window_bottom(hwnd)

# Save screenshot of the pygame surface
screenshot_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "screenshot.png"
)
pygame.image.save(screen, screenshot_path)
print(f"Screenshot saved to: {screenshot_path}")

# Run for a few more seconds
for i in range(90):  # 3 more seconds
    dt = clock.tick(30) / 1000.0
    for event in pygame.event.get():
        pass
    world.update(dt)
    world.draw(screen)
    pygame.display.flip()
    if hwnd:
        set_window_bottom(hwnd)

pygame.quit()
print("Test complete")
