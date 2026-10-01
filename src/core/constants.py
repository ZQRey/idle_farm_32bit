"""
Game constants and default configuration.
"""

# Version
VERSION = "0.1.0"
GAME_TITLE = "Desktop Idle Farm"

# Window defaults
DEFAULT_SCENE_HEIGHT = 180
MIN_SCENE_HEIGHT = 120
MAX_SCENE_HEIGHT = 220

# Rendering
DEFAULT_FPS = 30
LOW_POWER_FPS = 15
HIGH_FPS = 60
TILE_SIZE = 32

# Simulation
SIMULATION_TICKS_PER_SECOND = 8  # 8 ticks/sec
SIMULATION_TICK_INTERVAL = 1.0 / SIMULATION_TICKS_PER_SECOND

# Day/Night cycle
DAY_CYCLE_MINUTES = 40  # 40 real minutes = 1 game day
DAY_CYCLE_SECONDS = DAY_CYCLE_MINUTES * 60

# Crop cycle target
CROP_CYCLE_MINUTES = 18  # ~18 real minutes for full crop cycle

# Economy defaults
STARTING_MONEY = 5000
STARTING_FUEL = 200

# Save
AUTOSAVE_INTERVAL_SECONDS = 45
MAX_OFFLINE_HOURS = 12

# Paths
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
SAVES_DIR = os.path.join(BASE_DIR, "saves")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
LOCALIZATION_DIR = os.path.join(BASE_DIR, "localization")

# Colors (pixel-art palette)
class Colors:
    """Cozy farm color palette."""
    # Sky
    SKY_DAY = (135, 196, 240)
    SKY_DAWN = (255, 183, 120)
    SKY_EVENING = (200, 120, 80)
    SKY_NIGHT = (20, 24, 46)

    # Ground
    GRASS = (76, 145, 65)
    GRASS_DARK = (58, 120, 50)
    DIRT = (139, 100, 60)
    DIRT_PLOWED = (100, 70, 42)
    DIRT_WET = (80, 56, 34)

    # Crops
    WHEAT_YOUNG = (120, 170, 60)
    WHEAT_MATURE = (218, 185, 80)
    WHEAT_GOLDEN = (230, 195, 70)

    # Buildings
    BARN_RED = (170, 50, 40)
    BARN_DARK = (130, 38, 30)
    WOOD = (160, 120, 70)
    WOOD_DARK = (120, 88, 50)
    ROOF_GRAY = (120, 120, 130)
    STONE = (150, 148, 140)

    # Vehicles
    TRACTOR_GREEN = (60, 130, 50)
    TRACTOR_RED = (180, 50, 40)
    METAL_GRAY = (140, 145, 150)
    TIRE_BLACK = (40, 40, 45)
    WHEEL_YELLOW = (200, 180, 60)

    # Workers
    SKIN = (230, 190, 150)
    SHIRT_BLUE = (70, 110, 170)
    PANTS_BROWN = (100, 75, 50)
    HAT_STRAW = (220, 200, 130)

    # UI
    UI_BG = (40, 44, 52)
    UI_BG_LIGHT = (55, 60, 70)
    UI_BORDER = (80, 85, 95)
    UI_TEXT = (230, 230, 235)
    UI_TEXT_DIM = (160, 165, 170)
    UI_ACCENT = (100, 180, 90)
    UI_ACCENT_HOVER = (120, 200, 110)
    UI_DANGER = (200, 70, 60)
    UI_GOLD = (230, 195, 70)

    # Weather
    RAIN_DROP = (160, 200, 240)
    SNOW_FLAKE = (230, 235, 245)
    CLOUD = (200, 205, 215)
    FOG = (180, 185, 195)

    # Nature
    TREE_GREEN = (50, 120, 45)
    TREE_TRUNK = (100, 70, 40)
    FLOWER_RED = (210, 60, 50)
    FLOWER_YELLOW = (240, 210, 60)
    WATER = (70, 140, 200)

    # Transparent
    TRANSPARENT = (0, 0, 0, 0)

    # Night overlay
    NIGHT_TINT = (20, 24, 46, 100)
    DAWN_TINT = (255, 183, 120, 40)
    EVENING_TINT = (200, 120, 80, 60)

    # Light
    LAMP_GLOW = (255, 220, 120, 80)
    WINDOW_GLOW = (255, 230, 150)
