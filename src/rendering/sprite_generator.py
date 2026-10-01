"""
Pixel Art Sprite Generator for Desktop Idle Farm.
Generates all game sprites programmatically using Pillow.
Each sprite is a proper pixel-art image with the game's color palette.
"""
import os
import logging
from PIL import Image, ImageDraw

logger = logging.getLogger("sprite_gen")

# === COLOR PALETTE ===
# Warm, cozy farm palette
C = {
    # Sky
    'sky': (135, 196, 240),
    'sky_dawn': (255, 183, 120),
    'sky_night': (20, 24, 46),

    # Ground
    'grass1': (76, 145, 65),
    'grass2': (90, 160, 75),
    'grass3': (65, 130, 55),
    'dirt1': (139, 100, 60),
    'dirt2': (120, 85, 50),
    'dirt3': (100, 70, 42),
    'dirt_wet': (80, 56, 34),
    'dirt_plowed': (90, 62, 38),
    'path': (175, 150, 110),

    # Crops
    'seed': (100, 75, 45),
    'sprout': (100, 160, 55),
    'young_green': (85, 150, 50),
    'wheat_green': (120, 170, 60),
    'wheat_gold': (218, 185, 80),
    'wheat_ripe': (230, 195, 70),
    'wheat_stalk': (180, 155, 65),

    # Buildings
    'barn_red': (170, 50, 40),
    'barn_dark': (130, 38, 30),
    'wood': (160, 120, 70),
    'wood_dark': (120, 88, 50),
    'wood_light': (190, 150, 95),
    'roof_gray': (120, 120, 130),
    'roof_dark': (90, 90, 100),
    'stone': (150, 148, 140),
    'stone_dark': (120, 118, 112),
    'window_glow': (255, 230, 150),
    'white': (240, 240, 235),

    # Vehicles
    'tractor_green': (60, 130, 50),
    'tractor_green_dark': (45, 100, 38),
    'tractor_red': (180, 50, 40),
    'tractor_red_dark': (140, 35, 28),
    'metal': (140, 145, 150),
    'metal_dark': (100, 105, 110),
    'metal_light': (170, 175, 180),
    'tire': (40, 40, 45),
    'tire_hub': (90, 90, 95),
    'wheel_rim': (200, 180, 60),
    'exhaust': (80, 80, 85),
    'glass': (160, 200, 220),
    'headlight': (255, 240, 180),

    # Combine
    'combine_yellow': (210, 180, 50),
    'combine_dark': (170, 145, 40),
    'combine_header': (150, 150, 155),

    # Truck
    'truck_blue': (60, 90, 150),
    'truck_blue_dark': (45, 68, 115),

    # Workers
    'skin': (230, 190, 150),
    'skin_dark': (200, 165, 130),
    'hair_brown': (80, 55, 35),
    'hair_blond': (200, 175, 100),
    'shirt_blue': (70, 110, 170),
    'shirt_red': (170, 60, 50),
    'shirt_green': (60, 120, 55),
    'pants': (100, 75, 50),
    'pants_dark': (75, 55, 38),
    'boots': (65, 45, 30),
    'hat': (220, 200, 130),
    'hat_dark': (190, 170, 110),
    'overall': (70, 90, 140),

    # Animals
    'dog_brown': (160, 110, 60),
    'dog_dark': (120, 80, 42),
    'dog_belly': (200, 170, 120),
    'cat_orange': (210, 140, 50),
    'cat_dark': (170, 110, 35),
    'cat_belly': (230, 210, 170),

    # Nature
    'tree_green': (50, 120, 45),
    'tree_dark': (35, 90, 32),
    'tree_light': (70, 145, 60),
    'trunk': (100, 70, 40),
    'trunk_dark': (75, 52, 30),
    'flower_red': (210, 60, 50),
    'flower_yellow': (240, 210, 60),
    'flower_white': (240, 235, 225),
    'flower_purple': (150, 70, 160),
    'fence': (175, 145, 100),
    'fence_dark': (140, 115, 78),

    # Weather
    'rain': (160, 200, 240),
    'snow': (230, 235, 245),
    'hail': (200, 210, 225),
    'cloud': (210, 215, 225),
    'cloud_dark': (150, 155, 165),
    'lightning': (255, 255, 200),
    'puddle': (100, 150, 190),

    # Misc
    'transparent': (255, 0, 255),  # Magenta = transparent
    'black': (20, 20, 25),
    'shadow': (0, 0, 0, 80),
}


def _px(draw, x, y, color):
    """Draw a single pixel."""
    if len(color) == 4:
        draw.point((x, y), fill=color[:3])
    else:
        draw.point((x, y), fill=color)


def _rect(draw, x, y, w, h, color):
    """Draw a filled rectangle."""
    draw.rectangle([x, y, x + w - 1, y + h - 1], fill=color)


def _line_h(draw, x, y, length, color):
    """Draw horizontal line."""
    draw.line([(x, y), (x + length - 1, y)], fill=color)


def _line_v(draw, x, y, length, color):
    """Draw vertical line."""
    draw.line([(x, y), (x, y + length - 1)], fill=color)


class SpriteGenerator:
    """Generates all pixel-art sprites for the game."""

    def __init__(self, assets_dir: str):
        self.assets_dir = assets_dir
        self.generated_count = 0

    def generate_all(self):
        """Generate all game sprites."""
        logger.info("Generating pixel-art sprites...")

        self._generate_terrain()
        self._generate_crops()
        self._generate_buildings()
        self._generate_tractors()
        self._generate_combines()
        self._generate_trucks()
        self._generate_workers()
        self._generate_animals()
        self._generate_environment()
        self._generate_weather()
        self._generate_ui()
        self._generate_particles()

        logger.info(f"Generated {self.generated_count} sprites")

    def _save(self, img: Image.Image, subdir: str, name: str):
        """Save sprite to assets directory."""
        path = os.path.join(self.assets_dir, subdir)
        os.makedirs(path, exist_ok=True)
        filepath = os.path.join(path, f"{name}.png")
        # Convert RGBA to RGB with magenta background for color-key transparency
        if img.mode == 'RGBA':
            bg = Image.new('RGBA', img.size, C['transparent'] + (255,))
            bg.paste(img, mask=img)
            img = bg.convert('RGB')
        img.save(filepath)
        self.generated_count += 1

    def _save_rgba(self, img: Image.Image, subdir: str, name: str):
        """Save sprite with proper alpha channel."""
        path = os.path.join(self.assets_dir, subdir)
        os.makedirs(path, exist_ok=True)
        filepath = os.path.join(path, f"{name}.png")
        img.save(filepath)
        self.generated_count += 1

    # ========== TERRAIN ==========

    def _generate_terrain(self):
        """Generate terrain tiles."""
        logger.info("  Generating terrain...")

        # Grass tile
        img = Image.new('RGB', (32, 32), C['grass1'])
        draw = ImageDraw.Draw(img)
        # Add subtle variation
        for y in range(32):
            for x in range(32):
                if (x + y) % 7 == 0:
                    _px(draw, x, y, C['grass2'])
                elif (x * 3 + y * 5) % 13 == 0:
                    _px(draw, x, y, C['grass3'])
        # Small grass blades
        for x in range(2, 30, 5):
            _px(draw, x, 10, C['grass2'])
            _px(draw, x, 9, C['grass2'])
            _px(draw, x + 1, 20, C['grass3'])
        self._save(img, 'terrain', 'grass')

        # Dirt tile
        img = Image.new('RGB', (32, 32), C['dirt1'])
        draw = ImageDraw.Draw(img)
        for y in range(32):
            for x in range(32):
                if (x + y * 3) % 11 == 0:
                    _px(draw, x, y, C['dirt2'])
                elif (x * 7 + y) % 17 == 0:
                    _px(draw, x, y, C['dirt3'])
        self._save(img, 'terrain', 'dirt')

        # Plowed dirt
        img = Image.new('RGB', (32, 32), C['dirt_plowed'])
        draw = ImageDraw.Draw(img)
        for row in range(0, 32, 4):
            _rect(draw, 0, row, 32, 2, C['dirt3'])
            _rect(draw, 0, row + 2, 32, 2, C['dirt_plowed'])
        self._save(img, 'terrain', 'dirt_plowed')

        # Cultivated dirt
        img = Image.new('RGB', (32, 32), C['dirt2'])
        draw = ImageDraw.Draw(img)
        for row in range(0, 32, 4):
            _rect(draw, 0, row, 32, 1, C['dirt3'])
            _rect(draw, 0, row + 1, 32, 3, C['dirt2'])
            for x in range(2, 30, 6):
                _px(draw, x, row + 2, C['dirt1'])
        self._save(img, 'terrain', 'dirt_cultivated')

        # Seeded dirt
        img = Image.new('RGB', (32, 32), C['dirt2'])
        draw = ImageDraw.Draw(img)
        for row in range(0, 32, 4):
            _rect(draw, 0, row, 32, 1, C['dirt3'])
            _rect(draw, 0, row + 1, 32, 3, C['dirt2'])
            for x in range(4, 30, 8):
                _px(draw, x, row + 2, C['seed'])
                _px(draw, x + 1, row + 2, C['seed'])
        self._save(img, 'terrain', 'dirt_seeded')

        # Wet dirt
        img = Image.new('RGB', (32, 32), C['dirt_wet'])
        draw = ImageDraw.Draw(img)
        for y in range(32):
            for x in range(32):
                if (x + y * 2) % 9 == 0:
                    _px(draw, x, y, C['dirt3'])
        self._save(img, 'terrain', 'dirt_wet')

        # Path
        img = Image.new('RGB', (32, 32), C['path'])
        draw = ImageDraw.Draw(img)
        for y in range(32):
            for x in range(32):
                if (x * 3 + y * 7) % 19 == 0:
                    _px(draw, x, y, C['dirt1'])
        self._save(img, 'terrain', 'path')

        # Snow
        img = Image.new('RGB', (32, 32), C['snow'])
        draw = ImageDraw.Draw(img)
        for y in range(32):
            for x in range(32):
                if (x + y) % 11 == 0:
                    _px(draw, x, y, (220, 225, 235))
        self._save(img, 'terrain', 'snow')

    # ========== CROPS ==========

    def _generate_crops(self):
        """Generate crop sprites for each growth stage."""
        logger.info("  Generating crops...")

        crop_colors = {
            'wheat': {
                'sprout': C['sprout'],
                'young': C['young_green'],
                'growing': C['wheat_green'],
                'mature': C['wheat_gold'],
                'ripe': C['wheat_ripe'],
                'stalk': C['wheat_stalk'],
            },
            'barley': {
                'sprout': (90, 155, 50),
                'young': (80, 145, 48),
                'growing': (115, 165, 55),
                'mature': (200, 175, 75),
                'ripe': (215, 185, 70),
                'stalk': (170, 150, 60),
            },
            'corn': {
                'sprout': (95, 165, 55),
                'young': (80, 150, 45),
                'growing': (100, 160, 50),
                'mature': (120, 170, 55),
                'ripe': (240, 210, 70),
                'stalk': (110, 155, 50),
            },
            'sunflower': {
                'sprout': (90, 155, 50),
                'young': (80, 145, 45),
                'growing': (100, 160, 50),
                'mature': (240, 210, 60),
                'ripe': (230, 200, 50),
                'stalk': (90, 140, 45),
            },
        }

        for crop_name, colors in crop_colors.items():
            self._generate_crop_stages(crop_name, colors)

    def _generate_crop_stages(self, name: str, colors: dict):
        """Generate all growth stages for a crop type."""

        # Seed stage - small dots in dirt
        img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for x in range(6, 28, 8):
            _px(draw, x, 28, C['seed'])
            _px(draw, x + 1, 28, C['seed'])
        self._save_rgba(img, f'crops/{name}', 'seed')

        # Sprout stage - tiny green dots
        img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for x in range(6, 28, 8):
            _px(draw, x, 27, colors['sprout'])
            _px(draw, x, 28, colors['sprout'])
            _px(draw, x + 1, 28, C['seed'])
        self._save_rgba(img, f'crops/{name}', 'sprout')

        # Young stage - small stalks
        img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for x in range(4, 28, 6):
            _line_v(draw, x, 24, 6, colors['young'])
            _px(draw, x - 1, 25, colors['young'])
            _px(draw, x + 1, 25, colors['young'])
        self._save_rgba(img, f'crops/{name}', 'young')

        # Growing stage - taller stalks
        img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for x in range(3, 29, 5):
            _line_v(draw, x, 18, 12, colors['growing'])
            _px(draw, x - 1, 20, colors['growing'])
            _px(draw, x + 1, 19, colors['growing'])
            _px(draw, x - 1, 23, colors['growing'])
        self._save_rgba(img, f'crops/{name}', 'growing')

        # Mature stage - full height with heads
        img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for x in range(2, 30, 4):
            _line_v(draw, x, 14, 16, colors['stalk'])
            # Grain head
            _px(draw, x, 13, colors['mature'])
            _px(draw, x, 12, colors['mature'])
            _px(draw, x - 1, 13, colors['mature'])
            _px(draw, x + 1, 13, colors['mature'])
            # Leaves
            _px(draw, x - 1, 18, colors['growing'])
            _px(draw, x + 1, 22, colors['growing'])
        self._save_rgba(img, f'crops/{name}', 'mature')

        # Harvest-ready - golden/ripe
        img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for x in range(2, 30, 4):
            _line_v(draw, x, 12, 18, colors['stalk'])
            # Full grain head
            _rect(draw, x - 1, 10, 3, 3, colors['ripe'])
            _px(draw, x, 9, colors['ripe'])
            # Drooping effect
            _px(draw, x + 1, 11, colors['ripe'])
        self._save_rgba(img, f'crops/{name}', 'ready')

        # Harvested - stubble
        img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for x in range(3, 29, 5):
            _line_v(draw, x, 27, 3, colors['stalk'])
        self._save_rgba(img, f'crops/{name}', 'harvested')

    # ========== BUILDINGS ==========

    def _generate_buildings(self):
        """Generate building sprites."""
        logger.info("  Generating buildings...")

        # Farmhouse (64x48)
        img = Image.new('RGBA', (64, 48), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Main structure
        _rect(draw, 8, 20, 48, 26, C['wood'])
        _rect(draw, 8, 20, 48, 2, C['wood_dark'])

        # Roof
        for i in range(12):
            _rect(draw, 8 - 1 + i // 2, 8 + i, 50 + 2 - i, 1, C['barn_red'] if i % 2 == 0 else C['barn_dark'])

        # Door
        _rect(draw, 28, 30, 8, 16, C['wood_dark'])
        _rect(draw, 29, 31, 6, 14, C['wood'])
        _px(draw, 34, 38, C['wheel_rim'])  # doorknob

        # Windows
        _rect(draw, 14, 28, 8, 8, C['glass'])
        _rect(draw, 14, 28, 8, 1, C['wood_dark'])
        _rect(draw, 14, 35, 8, 1, C['wood_dark'])
        _rect(draw, 14, 28, 1, 8, C['wood_dark'])
        _rect(draw, 21, 28, 1, 8, C['wood_dark'])
        _px(draw, 17, 32, C['wood_dark'])  # cross

        _rect(draw, 42, 28, 8, 8, C['glass'])
        _rect(draw, 42, 28, 8, 1, C['wood_dark'])
        _rect(draw, 42, 35, 8, 1, C['wood_dark'])
        _rect(draw, 42, 28, 1, 8, C['wood_dark'])
        _rect(draw, 49, 28, 1, 8, C['wood_dark'])
        _px(draw, 45, 32, C['wood_dark'])

        # Chimney
        _rect(draw, 46, 4, 6, 10, C['stone'])
        _rect(draw, 46, 4, 6, 1, C['stone_dark'])

        # Foundation
        _rect(draw, 6, 44, 52, 4, C['stone'])
        self._save_rgba(img, 'buildings', 'farmhouse')

        # Farmhouse night version (windows glow)
        img_night = img.copy()
        draw = ImageDraw.Draw(img_night)
        _rect(draw, 15, 29, 6, 6, C['window_glow'])
        _rect(draw, 43, 29, 6, 6, C['window_glow'])
        self._save_rgba(img_night, 'buildings', 'farmhouse_night')

        # Barn (64x48)
        img = Image.new('RGBA', (64, 48), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Main structure
        _rect(draw, 4, 16, 56, 30, C['barn_red'])
        _rect(draw, 4, 16, 56, 2, C['barn_dark'])

        # Roof
        for i in range(10):
            w = 60 - i * 2
            x = 2 + i
            _rect(draw, x, 6 + i, w, 1, C['roof_gray'] if i % 2 == 0 else C['roof_dark'])

        # Barn door (large)
        _rect(draw, 20, 24, 24, 22, C['wood_dark'])
        _rect(draw, 21, 25, 10, 20, C['wood'])
        _rect(draw, 33, 25, 10, 20, C['wood'])

        # Cross beams on door
        for dy in range(0, 20, 5):
            _line_h(draw, 21, 25 + dy, 10, C['wood_dark'])
            _line_h(draw, 33, 25 + dy, 10, C['wood_dark'])

        # Side windows
        _rect(draw, 8, 24, 6, 6, C['glass'])
        _rect(draw, 50, 24, 6, 6, C['glass'])

        # Silo detail on side
        _rect(draw, 4, 16, 2, 30, C['barn_dark'])
        _rect(draw, 58, 16, 2, 30, C['barn_dark'])

        # Foundation
        _rect(draw, 2, 44, 60, 4, C['stone'])
        self._save_rgba(img, 'buildings', 'barn')

        # Storage/Warehouse (48x32)
        img = Image.new('RGBA', (48, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 2, 8, 44, 22, C['metal'])
        _rect(draw, 2, 8, 44, 2, C['metal_dark'])
        # Corrugated roof
        for i in range(6):
            _rect(draw, 2 + i, 2 + i, 44 - i * 2, 1, C['metal_light'] if i % 2 == 0 else C['metal'])
        # Door
        _rect(draw, 18, 14, 12, 16, C['metal_dark'])
        _rect(draw, 19, 15, 10, 14, C['metal'])
        # Foundation
        _rect(draw, 0, 28, 48, 4, C['stone'])
        self._save_rgba(img, 'buildings', 'storage')

        # Silo (24x48)
        img = Image.new('RGBA', (24, 48), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Cylinder body
        _rect(draw, 4, 12, 16, 34, C['metal'])
        _rect(draw, 4, 12, 1, 34, C['metal_dark'])
        _rect(draw, 19, 12, 1, 34, C['metal_dark'])
        # Top dome
        _rect(draw, 6, 8, 12, 4, C['metal_light'])
        _rect(draw, 8, 6, 8, 2, C['metal_light'])
        _rect(draw, 10, 4, 4, 2, C['metal'])
        # Bands
        for y in range(16, 44, 6):
            _line_h(draw, 4, y, 16, C['metal_dark'])
        _rect(draw, 2, 44, 20, 4, C['stone'])
        self._save_rgba(img, 'buildings', 'silo')

        # Windmill Tower (32x48)
        img = Image.new('RGBA', (32, 48), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Stone/timber base tapers towards top
        for y in range(12, 46):
            inset = (46 - y) // 7
            w = 24 - inset * 2
            x = 4 + inset
            color = C['wood'] if y % 4 != 0 else C['wood_dark']
            _rect(draw, x, y, w, 1, color)
        # Wooden beams
        _line_v(draw, 10, 16, 28, C['wood_dark'])
        _line_v(draw, 21, 16, 28, C['wood_dark'])
        # Door
        _rect(draw, 13, 34, 6, 12, C['wood_dark'])
        # Small window
        _rect(draw, 14, 20, 4, 5, C['glass'])
        # Conical roof
        for r in range(12):
            rw = 26 - r * 2
            rx = 3 + r
            _rect(draw, rx, 12 - r, rw, 1, C['roof_dark'] if r % 2 == 0 else C['roof_gray'])
        # Hub for blades
        _rect(draw, 14, 11, 4, 4, C['metal_dark'])
        # Stone foundation
        _rect(draw, 2, 44, 28, 4, C['stone'])
        self._save_rgba(img, 'buildings', 'windmill_tower')

        # Windmill Blades (4 animation frames, 32x32)
        import math
        for frame in range(4):
            img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            cx, cy = 16, 16
            base_angle = frame * (math.pi / 8)  # 22.5 deg per frame
            for blade in range(4):
                angle = base_angle + blade * (math.pi / 2)
                # Draw wooden sail arm
                for dist in range(2, 14):
                    bx = int(cx + math.cos(angle) * dist)
                    by = int(cy + math.sin(angle) * dist)
                    _px(draw, bx, by, C['wood_dark'])
                    # Sail cloth offset
                    if dist >= 4:
                        cx_offset = int(-math.sin(angle) * 2)
                        cy_offset = int(math.cos(angle) * 2)
                        _px(draw, bx + cx_offset, by + cy_offset, C['white'])
            _rect(draw, 15, 15, 3, 3, C['metal'])
            self._save_rgba(img, 'buildings', f'windmill_blades_{frame}')

        # Doghouse (16x16)
        img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 2, 6, 12, 10, C['wood'])
        _rect(draw, 2, 6, 12, 1, C['wood_dark'])
        # Roof
        for i in range(5):
            _rect(draw, 1 + i, 5 - i, 14 - i * 2, 1, C['barn_red'])
        # Entrance
        _rect(draw, 6, 9, 5, 7, C['black'])
        self._save_rgba(img, 'buildings', 'doghouse')

        # Water Well (20x24)
        img = Image.new('RGBA', (20, 24), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Stone base
        _rect(draw, 3, 14, 14, 10, C['stone'])
        _rect(draw, 3, 14, 14, 2, C['stone_dark'])
        # Water inside
        _rect(draw, 5, 14, 10, 2, (70, 140, 200))
        # Wooden pillars
        _line_v(draw, 4, 5, 10, C['wood_dark'])
        _line_v(draw, 15, 5, 10, C['wood_dark'])
        # Roof
        for i in range(5):
            _rect(draw, 2 + i, 5 - i, 16 - i * 2, 1, C['roof_dark'])
        # Bucket & Rope
        _line_v(draw, 10, 5, 5, C['wood_light'])
        _rect(draw, 9, 10, 3, 3, C['wood_dark'])
        self._save_rgba(img, 'buildings', 'well')

    # ========== TRACTORS ==========

    def _generate_tractors(self):
        """Generate tractor sprites with animations."""
        logger.info("  Generating tractors...")

        # Small old tractor - facing right (48x32)
        self._draw_tractor('small_tractor', 48, 32,
                          body_color=C['tractor_green'],
                          body_dark=C['tractor_green_dark'],
                          front_wheel_r=4, rear_wheel_r=7,
                          body_w=22, body_h=14, cab_h=8)

        # Medium tractor - facing right (48x32)
        self._draw_tractor('medium_tractor', 48, 32,
                          body_color=C['tractor_red'],
                          body_dark=C['tractor_red_dark'],
                          front_wheel_r=5, rear_wheel_r=8,
                          body_w=24, body_h=14, cab_h=9)

    def _draw_tractor(self, name, w, h, body_color, body_dark,
                      front_wheel_r, rear_wheel_r, body_w, body_h, cab_h):
        """Draw a tractor sprite. Creates idle and driving frames."""
        frames = []

        for frame in range(4):  # 4 animation frames
            img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Calculate positions
            bx = (w - body_w) // 2 - 2
            by = h - rear_wheel_r * 2 - body_h + 2

            # Engine hood
            hood_w = body_w // 2
            _rect(draw, bx, by + 4, hood_w, body_h - 4, body_color)
            _rect(draw, bx, by + 4, hood_w, 2, body_dark)
            # Grill
            for gy in range(by + 7, by + body_h - 1, 2):
                _line_h(draw, bx + 1, gy, hood_w - 2, body_dark)

            # Cab
            cab_x = bx + hood_w - 2
            cab_w = body_w - hood_w + 2
            _rect(draw, cab_x, by - cab_h + 4, cab_w, cab_h + body_h - 4, body_color)
            _rect(draw, cab_x, by - cab_h + 4, cab_w, 1, body_dark)

            # Cab window
            _rect(draw, cab_x + 2, by - cab_h + 6, cab_w - 4, cab_h - 4, C['glass'])

            # Exhaust pipe
            _rect(draw, bx + 2, by - 2, 2, 6, C['exhaust'])
            # Smoke (varies per frame)
            if frame % 2 == 0:
                _px(draw, bx + 2, by - 3, (150, 150, 155))
                _px(draw, bx + 3, by - 4, (170, 170, 175))

            # Headlight
            _px(draw, bx, by + 6, C['headlight'])
            _px(draw, bx, by + 7, C['headlight'])

            # Rear wheel
            rear_cx = bx + body_w - rear_wheel_r - 1
            rear_cy = h - rear_wheel_r - 1
            self._draw_wheel(draw, rear_cx, rear_cy, rear_wheel_r, frame)

            # Front wheel
            front_cx = bx + front_wheel_r + 2
            front_cy = h - front_wheel_r - 1
            self._draw_wheel(draw, front_cx, front_cy, front_wheel_r, frame)

            # Hitch point
            _rect(draw, bx + body_w, by + body_h - 4, 3, 2, C['metal_dark'])

            frames.append(img)
            self._save_rgba(img, f'tractors/{name}', f'right_{frame}')

        # Generate left-facing frames (mirror)
        for i, img in enumerate(frames):
            flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
            self._save_rgba(flipped, f'tractors/{name}', f'left_{i}')

    def _draw_wheel(self, draw, cx, cy, radius, frame=0):
        """Draw a pixel-art wheel with rotation animation."""
        # Draw circle (pixel art style)
        for y in range(-radius, radius + 1):
            for x in range(-radius, radius + 1):
                dist = (x * x + y * y) ** 0.5
                if dist <= radius:
                    if dist <= radius - 2:
                        # Hub
                        if dist <= 2:
                            _px(draw, cx + x, cy + y, C['tire_hub'])
                        else:
                            _px(draw, cx + x, cy + y, C['tire'])
                    else:
                        # Tire edge
                        _px(draw, cx + x, cy + y, C['tire'])

        # Rim spokes (rotate with frame)
        spoke_offsets = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        offset = frame % 4
        for i, (dx, dy) in enumerate(spoke_offsets):
            si = (i + offset) % 4
            sdx, sdy = spoke_offsets[si]
            for d in range(1, radius - 1):
                _px(draw, cx + sdx * d, cy + sdy * d, C['tire_hub'])

    # ========== COMBINES ==========

    def _generate_combines(self):
        """Generate combine harvester sprites."""
        logger.info("  Generating combines...")

        for frame in range(4):
            img = Image.new('RGBA', (96, 48), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Main body
            _rect(draw, 30, 10, 36, 28, C['combine_yellow'])
            _rect(draw, 30, 10, 36, 2, C['combine_dark'])

            # Cab
            _rect(draw, 50, 4, 16, 16, C['combine_yellow'])
            _rect(draw, 52, 6, 12, 10, C['glass'])

            # Grain tank
            _rect(draw, 30, 8, 20, 8, C['combine_dark'])
            _rect(draw, 30, 8, 20, 1, C['combine_yellow'])

            # Header (cutting platform)
            _rect(draw, 2, 28, 30, 10, C['combine_header'])
            _rect(draw, 2, 28, 30, 2, C['metal_dark'])
            # Reel
            reel_y = 24
            _rect(draw, 4, reel_y, 26, 4, C['metal'])
            # Reel bars rotate
            for bx in range(6, 28, 6):
                bar_offset = (frame * 2 + bx) % 6
                _line_v(draw, bx + bar_offset % 3, reel_y, 4, C['metal_dark'])

            # Auger
            _rect(draw, 68, 12, 20, 4, C['metal'])
            _rect(draw, 85, 6, 4, 10, C['metal'])

            # Wheels
            self._draw_wheel(draw, 38, 42, 5, frame)
            self._draw_wheel(draw, 58, 42, 5, frame)

            # Exhaust
            _rect(draw, 46, 4, 2, 6, C['exhaust'])
            if frame % 2 == 0:
                _px(draw, 46, 3, (150, 150, 155))

            self._save_rgba(img, 'combines/small_combine', f'right_{frame}')

            # Mirror for left
            flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
            self._save_rgba(flipped, 'combines/small_combine', f'left_{frame}')

    # ========== TRUCKS ==========

    def _generate_trucks(self):
        """Generate truck sprites."""
        logger.info("  Generating trucks...")

        for frame in range(4):
            img = Image.new('RGBA', (64, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Cab
            _rect(draw, 2, 8, 18, 18, C['truck_blue'])
            _rect(draw, 2, 8, 18, 2, C['truck_blue_dark'])
            # Cab window
            _rect(draw, 4, 10, 8, 8, C['glass'])
            # Headlight
            _px(draw, 2, 18, C['headlight'])

            # Bed/trailer
            _rect(draw, 20, 6, 38, 20, C['metal'])
            _rect(draw, 20, 6, 38, 2, C['metal_dark'])
            _rect(draw, 20, 6, 1, 20, C['metal_dark'])
            _rect(draw, 57, 6, 1, 20, C['metal_dark'])

            # Wheels
            self._draw_wheel(draw, 10, 28, 3, frame)
            self._draw_wheel(draw, 30, 28, 3, frame)
            self._draw_wheel(draw, 48, 28, 3, frame)

            # Tail light
            _px(draw, 57, 20, C['tractor_red'])

            self._save_rgba(img, 'trucks/farm_truck', f'right_{frame}')
            flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
            self._save_rgba(flipped, 'trucks/farm_truck', f'left_{frame}')

    # ========== WORKERS ==========

    def _generate_workers(self):
        """Generate worker character sprites."""
        logger.info("  Generating workers...")

        # Worker idle (16x32)
        self._draw_worker_set('worker1', C['shirt_blue'], C['hair_brown'])
        self._draw_worker_set('worker2', C['shirt_red'], C['hair_blond'])

    def _draw_worker_set(self, name: str, shirt_color, hair_color):
        """Generate a full set of worker animations."""

        for direction in ['right', 'left']:
            for frame in range(4):
                img = Image.new('RGBA', (16, 32), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)

                # Hat
                _rect(draw, 4, 2, 8, 3, C['hat'])
                _rect(draw, 3, 4, 10, 1, C['hat_dark'])

                # Head
                _rect(draw, 5, 5, 6, 6, C['skin'])
                # Eyes
                _px(draw, 6, 7, C['black'])
                _px(draw, 9, 7, C['black'])
                # Hair
                _rect(draw, 5, 5, 6, 1, hair_color)
                _px(draw, 5, 6, hair_color)
                _px(draw, 10, 6, hair_color)

                # Body/shirt
                _rect(draw, 4, 11, 8, 8, shirt_color)

                # Arms - animate for walking
                arm_offset = [0, -1, 0, 1][frame]
                _rect(draw, 3, 12 + arm_offset, 1, 5, C['skin'])
                _rect(draw, 12, 12 - arm_offset, 1, 5, C['skin'])

                # Pants
                _rect(draw, 5, 19, 3, 6, C['pants'])
                _rect(draw, 8, 19, 3, 6, C['pants'])

                # Leg animation for walking
                leg_offset = [0, 1, 0, -1][frame]
                _rect(draw, 5, 19, 3, 6 + leg_offset, C['pants'])
                _rect(draw, 8, 19, 3, 6 - leg_offset, C['pants'])

                # Boots
                _rect(draw, 4, 25 + leg_offset, 4, 3, C['boots'])
                _rect(draw, 8, 25 - leg_offset, 4, 3, C['boots'])

                if direction == 'left':
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)

                self._save_rgba(img, f'workers/{name}', f'{direction}_{frame}')

        # Idle frame
        img = Image.new('RGBA', (16, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 4, 2, 8, 3, C['hat'])
        _rect(draw, 3, 4, 10, 1, C['hat_dark'])
        _rect(draw, 5, 5, 6, 6, C['skin'])
        _px(draw, 6, 7, C['black'])
        _px(draw, 9, 7, C['black'])
        _rect(draw, 5, 5, 6, 1, hair_color)
        _rect(draw, 4, 11, 8, 8, shirt_color)
        _rect(draw, 3, 12, 1, 5, C['skin'])
        _rect(draw, 12, 12, 1, 5, C['skin'])
        _rect(draw, 5, 19, 3, 7, C['pants'])
        _rect(draw, 8, 19, 3, 7, C['pants'])
        _rect(draw, 4, 26, 4, 3, C['boots'])
        _rect(draw, 8, 26, 4, 3, C['boots'])
        self._save_rgba(img, f'workers/{name}', 'idle')

    # ========== ANIMALS ==========

    def _generate_animals(self):
        """Generate animal sprites."""
        logger.info("  Generating animals...")

        # Dog (16x16)
        for frame in range(4):
            img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            leg_offset = [0, 1, 0, -1][frame]

            # Body
            _rect(draw, 3, 6, 10, 5, C['dog_brown'])
            _rect(draw, 3, 9, 10, 2, C['dog_belly'])

            # Head
            _rect(draw, 11, 4, 4, 4, C['dog_brown'])
            _px(draw, 14, 5, C['black'])  # eye
            _px(draw, 14, 7, C['black'])  # nose

            # Ears
            _px(draw, 11, 3, C['dog_dark'])
            _px(draw, 13, 3, C['dog_dark'])

            # Tail
            _rect(draw, 1, 4 + (frame % 2), 2, 2, C['dog_brown'])

            # Legs
            _line_v(draw, 4, 11, 3 + leg_offset, C['dog_dark'])
            _line_v(draw, 6, 11, 3 - leg_offset, C['dog_dark'])
            _line_v(draw, 10, 11, 3 - leg_offset, C['dog_dark'])
            _line_v(draw, 12, 11, 3 + leg_offset, C['dog_dark'])

            self._save_rgba(img, 'animals', f'dog_right_{frame}')
            flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
            self._save_rgba(flipped, 'animals', f'dog_left_{frame}')

        # Dog sleeping
        img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 3, 10, 10, 3, C['dog_brown'])
        _rect(draw, 3, 12, 10, 1, C['dog_belly'])
        _rect(draw, 11, 8, 4, 4, C['dog_brown'])
        _px(draw, 14, 10, C['black'])
        _rect(draw, 1, 10, 2, 2, C['dog_brown'])
        self._save_rgba(img, 'animals', 'dog_sleep')

        # Cat (12x12)
        for frame in range(4):
            img = Image.new('RGBA', (12, 12), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            leg_offset = [0, 1, 0, -1][frame]

            # Body
            _rect(draw, 2, 4, 8, 4, C['cat_orange'])
            # Head
            _rect(draw, 8, 2, 3, 3, C['cat_orange'])
            # Ears
            _px(draw, 8, 1, C['cat_dark'])
            _px(draw, 10, 1, C['cat_dark'])
            # Eye
            _px(draw, 10, 3, C['black'])
            # Tail
            _line_v(draw, 1, 2 + (frame % 2), 3, C['cat_dark'])
            # Legs
            _line_v(draw, 3, 8, 2 + leg_offset, C['cat_dark'])
            _line_v(draw, 5, 8, 2 - leg_offset, C['cat_dark'])
            _line_v(draw, 7, 8, 2 - leg_offset, C['cat_dark'])
            _line_v(draw, 9, 8, 2 + leg_offset, C['cat_dark'])

            self._save_rgba(img, 'animals', f'cat_right_{frame}')
            flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
            self._save_rgba(flipped, 'animals', f'cat_left_{frame}')

        # Cat sleeping
        img = Image.new('RGBA', (12, 12), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 2, 7, 8, 3, C['cat_orange'])
        _rect(draw, 8, 6, 3, 2, C['cat_orange'])
        _rect(draw, 1, 8, 2, 2, C['cat_dark'])  # tail
        self._save_rgba(img, 'animals', 'cat_sleep')

        # Cows (24x16, 2 frames: idle and grazing)
        for frame in range(2):
            img = Image.new('RGBA', (24, 16), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # Body
            _rect(draw, 5, 4, 14, 8, C['white'])
            # Black spots
            _rect(draw, 8, 4, 4, 4, C['black'])
            _rect(draw, 14, 6, 3, 4, C['black'])
            _rect(draw, 6, 8, 3, 3, C['black'])
            # Head (higher for idle, lowered for grazing)
            hy = 2 if frame == 0 else 5
            _rect(draw, 1, hy, 5, 5, C['white'])
            _px(draw, 2, hy, C['black'])  # spot
            _px(draw, 2, hy + 2, C['black'])  # eye
            _rect(draw, 1, hy + 3, 3, 2, (240, 180, 180))  # pink muzzle
            # Horns / ears
            _px(draw, 4, hy - 1, C['wood_light'])
            # Legs
            leg_y = 11
            _line_v(draw, 6, leg_y, 4, C['black'])
            _line_v(draw, 8, leg_y, 4, C['black'])
            _line_v(draw, 15, leg_y, 4, C['black'])
            _line_v(draw, 17, leg_y, 4, C['black'])
            # Tail
            _line_v(draw, 19, 5, 5 + frame, C['black'])
            self._save_rgba(img, 'animals', f'cow_{frame}')

        # Sheep (18x14, 2 frames: idle and grazing)
        for frame in range(2):
            img = Image.new('RGBA', (18, 14), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # Woolly body
            _rect(draw, 4, 3, 11, 7, (245, 245, 240))
            _rect(draw, 3, 4, 13, 5, (235, 235, 230))
            # Head
            hy = 3 if frame == 0 else 5
            _rect(draw, 1, hy, 4, 4, (60, 60, 65))
            _px(draw, 2, hy + 1, C['white'])  # eye
            # Legs
            _line_v(draw, 5, 10, 3, (50, 50, 55))
            _line_v(draw, 7, 10, 3, (50, 50, 55))
            _line_v(draw, 11, 10, 3, (50, 50, 55))
            _line_v(draw, 13, 10, 3, (50, 50, 55))
            self._save_rgba(img, 'animals', f'sheep_{frame}')

        # Chickens (8x8, 2 frames: idle and pecking)
        for frame in range(2):
            img = Image.new('RGBA', (8, 8), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            color = C['white']
            _rect(draw, 2, 2, 4, 3, color)
            if frame == 0:
                _rect(draw, 1, 1, 2, 2, color)  # head
                _px(draw, 1, 0, C['flower_red'])  # comb
                _px(draw, 0, 2, (240, 180, 50))  # beak
            else:
                _rect(draw, 1, 3, 2, 2, color)  # head down pecking
                _px(draw, 1, 2, C['flower_red'])
                _px(draw, 0, 5, (240, 180, 50))
            # Legs
            _line_v(draw, 3, 5, 2, (200, 160, 40))
            _line_v(draw, 4, 5, 2, (200, 160, 40))
            self._save_rgba(img, 'animals', f'chicken_{frame}')

    # ========== ENVIRONMENT ==========

    def _generate_environment(self):
        """Generate environmental objects."""
        logger.info("  Generating environment...")

        # Tree (24x40)
        img = Image.new('RGBA', (24, 40), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Trunk
        _rect(draw, 10, 22, 4, 16, C['trunk'])
        _rect(draw, 10, 22, 1, 16, C['trunk_dark'])
        # Crown
        _rect(draw, 4, 4, 16, 20, C['tree_green'])
        _rect(draw, 6, 2, 12, 4, C['tree_green'])
        _rect(draw, 8, 0, 8, 4, C['tree_light'])
        # Depth
        _rect(draw, 4, 4, 2, 20, C['tree_dark'])
        _rect(draw, 18, 4, 2, 20, C['tree_dark'])
        # Highlight
        _rect(draw, 8, 4, 4, 6, C['tree_light'])
        self._save_rgba(img, 'environment', 'tree')

        # Bush (16x12)
        img = Image.new('RGBA', (16, 12), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 2, 4, 12, 8, C['tree_green'])
        _rect(draw, 4, 2, 8, 4, C['tree_green'])
        _rect(draw, 4, 3, 4, 3, C['tree_light'])
        _rect(draw, 2, 4, 1, 8, C['tree_dark'])
        self._save_rgba(img, 'environment', 'bush')

        # Fence post (8x16)
        img = Image.new('RGBA', (8, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 2, 0, 4, 16, C['fence'])
        _rect(draw, 2, 0, 4, 1, C['fence_dark'])
        _rect(draw, 0, 4, 8, 2, C['fence'])
        _rect(draw, 0, 10, 8, 2, C['fence'])
        self._save_rgba(img, 'environment', 'fence')

        # Lamp post (8x24)
        img = Image.new('RGBA', (8, 24), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 3, 6, 2, 18, C['metal_dark'])
        _rect(draw, 1, 2, 6, 4, C['metal'])
        _rect(draw, 2, 3, 4, 2, C['headlight'])
        self._save_rgba(img, 'environment', 'lamp')

        # Hay bale (16x12)
        img = Image.new('RGBA', (16, 12), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 1, 2, 14, 10, C['wheat_gold'])
        _rect(draw, 1, 2, 14, 1, C['wheat_stalk'])
        _rect(draw, 1, 2, 1, 10, C['wheat_stalk'])
        # Binding
        _line_h(draw, 1, 6, 14, C['wood_dark'])
        self._save_rgba(img, 'environment', 'hay')

        # Crate (12x12)
        img = Image.new('RGBA', (12, 12), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 1, 1, 10, 10, C['wood'])
        _rect(draw, 1, 1, 10, 1, C['wood_dark'])
        _rect(draw, 1, 1, 1, 10, C['wood_dark'])
        _line_h(draw, 1, 5, 10, C['wood_dark'])
        _line_v(draw, 5, 1, 10, C['wood_dark'])
        self._save_rgba(img, 'environment', 'crate')

        # Flower clusters
        for color_name, color in [('red', C['flower_red']), ('yellow', C['flower_yellow']),
                                   ('white', C['flower_white']), ('purple', C['flower_purple'])]:
            img = Image.new('RGBA', (8, 8), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            _px(draw, 3, 2, color)
            _px(draw, 2, 3, color)
            _px(draw, 4, 3, color)
            _px(draw, 3, 4, color)
            _px(draw, 3, 3, (255, 255, 200))  # center
            _line_v(draw, 3, 5, 3, C['sprout'])
            self._save_rgba(img, 'environment', f'flower_{color_name}')

        # Stones
        img = Image.new('RGBA', (10, 6), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 1, 2, 8, 4, C['stone'])
        _rect(draw, 2, 1, 6, 2, C['stone'])
        _rect(draw, 1, 2, 8, 1, C['stone_dark'])
        self._save_rgba(img, 'environment', 'stone')

        # Scarecrow (16x24)
        img = Image.new('RGBA', (16, 24), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Wooden cross pole
        _line_v(draw, 7, 4, 18, C['wood_dark'])
        _line_h(draw, 2, 8, 12, C['wood_dark'])
        # Straw head & Hat
        _rect(draw, 6, 4, 4, 4, C['hat'])
        _rect(draw, 4, 3, 8, 2, C['hat_dark'])
        _px(draw, 7, 6, C['black'])
        _px(draw, 8, 6, C['black'])
        # Flannel shirt
        _rect(draw, 5, 8, 6, 8, C['shirt_red'])
        _rect(draw, 2, 8, 3, 3, C['shirt_red'])
        _rect(draw, 11, 8, 3, 3, C['shirt_red'])
        # Straw peeking out of sleeves
        _px(draw, 1, 9, C['wheat_gold'])
        _px(draw, 14, 9, C['wheat_gold'])
        # Patchy pants
        _rect(draw, 5, 15, 6, 5, C['overall'])
        _px(draw, 7, 17, (180, 80, 80))  # patch
        self._save_rgba(img, 'environment', 'scarecrow')

        # Horizontal Fence Segment (24x10)
        img = Image.new('RGBA', (24, 10), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Posts at ends
        _rect(draw, 0, 0, 3, 10, C['fence'])
        _rect(draw, 0, 0, 3, 1, C['fence_dark'])
        _rect(draw, 21, 0, 3, 10, C['fence'])
        _rect(draw, 21, 0, 3, 1, C['fence_dark'])
        # Rails
        _rect(draw, 0, 2, 24, 2, C['fence'])
        _rect(draw, 0, 2, 24, 1, C['fence_dark'])
        _rect(draw, 0, 6, 24, 2, C['fence'])
        _rect(draw, 0, 6, 24, 1, C['fence_dark'])
        self._save_rgba(img, 'environment', 'fence_h')

        # Pond (48x16)
        img = Image.new('RGBA', (48, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Water body
        _rect(draw, 4, 3, 40, 10, (60, 130, 190, 230))
        _rect(draw, 8, 1, 32, 14, (70, 145, 205, 240))
        _rect(draw, 12, 0, 24, 16, (80, 160, 215, 250))
        # Reeds / Cattails
        _line_v(draw, 5, 0, 6, (40, 100, 35))
        _rect(draw, 4, 1, 3, 3, (120, 80, 40))
        _line_v(draw, 42, 1, 5, (40, 100, 35))
        # Lily pad
        _rect(draw, 18, 5, 4, 3, (50, 140, 50))
        _px(draw, 20, 6, (255, 240, 245))  # flower
        self._save_rgba(img, 'environment', 'pond')

    # ========== WEATHER ==========

    def _generate_weather(self):
        """Generate weather effect sprites."""
        logger.info("  Generating weather...")

        # Rain drop
        img = Image.new('RGBA', (2, 8), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 0, 0, 1, 8, C['rain'] + (180,))
        _px(draw, 0, 0, C['rain'] + (100,))
        self._save_rgba(img, 'weather', 'raindrop')

        # Snow flake
        img = Image.new('RGBA', (4, 4), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _px(draw, 1, 0, C['snow'] + (200,))
        _px(draw, 0, 1, C['snow'] + (200,))
        _px(draw, 2, 1, C['snow'] + (200,))
        _px(draw, 1, 2, C['snow'] + (200,))
        _px(draw, 1, 1, (255, 255, 255, 255))
        self._save_rgba(img, 'weather', 'snowflake')

        # Hail
        img = Image.new('RGBA', (3, 3), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 0, 0, 3, 3, C['hail'] + (220,))
        _px(draw, 1, 0, (255, 255, 255, 255))
        self._save_rgba(img, 'weather', 'hail')

        # Cloud (48x20)
        img = Image.new('RGBA', (48, 20), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 8, 8, 32, 10, C['cloud'] + (180,))
        _rect(draw, 12, 4, 20, 8, C['cloud'] + (190,))
        _rect(draw, 18, 2, 12, 6, C['cloud'] + (200,))
        _rect(draw, 4, 10, 40, 6, C['cloud'] + (160,))
        self._save_rgba(img, 'weather', 'cloud')

        # Dark cloud
        img = Image.new('RGBA', (48, 20), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 8, 8, 32, 10, C['cloud_dark'] + (200,))
        _rect(draw, 12, 4, 20, 8, C['cloud_dark'] + (210,))
        _rect(draw, 18, 2, 12, 6, C['cloud_dark'] + (220,))
        _rect(draw, 4, 10, 40, 6, C['cloud_dark'] + (180,))
        self._save_rgba(img, 'weather', 'cloud_dark')

        # Puddle (12x4)
        img = Image.new('RGBA', (12, 4), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 2, 1, 8, 2, C['puddle'] + (120,))
        _rect(draw, 4, 0, 4, 1, C['puddle'] + (80,))
        self._save_rgba(img, 'weather', 'puddle')

    # ========== UI ==========

    def _generate_ui(self):
        """Generate UI elements."""
        logger.info("  Generating UI...")

        # Tray icon (16x16)
        img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Mini tractor
        _rect(draw, 2, 6, 8, 5, C['tractor_green'])
        _rect(draw, 6, 4, 4, 4, C['tractor_green'])
        _rect(draw, 7, 5, 2, 2, C['glass'])
        # Wheels
        _rect(draw, 3, 11, 3, 3, C['tire'])
        _rect(draw, 8, 11, 3, 3, C['tire'])
        # Ground
        _rect(draw, 0, 13, 16, 3, C['grass1'])
        # Sun
        _rect(draw, 12, 1, 3, 3, C['wheat_gold'])
        self._save_rgba(img, 'ui', 'tray_icon')

        # Coin icon (12x12)
        img = Image.new('RGBA', (12, 12), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 2, 2, 8, 8, C['wheat_gold'])
        _rect(draw, 3, 1, 6, 1, C['wheat_gold'])
        _rect(draw, 1, 3, 1, 6, C['wheat_stalk'])
        _rect(draw, 3, 10, 6, 1, C['wheat_stalk'])
        _rect(draw, 10, 3, 1, 6, C['wheat_gold'])
        # Dollar sign
        _line_v(draw, 5, 3, 6, C['wood_dark'])
        _line_h(draw, 4, 4, 4, C['wood_dark'])
        _line_h(draw, 4, 7, 4, C['wood_dark'])
        self._save_rgba(img, 'ui', 'coin')

    # ========== PARTICLES ==========

    def _generate_particles(self):
        """Generate particle sprites."""
        logger.info("  Generating particles...")

        # Dust (4x4)
        for i in range(3):
            img = Image.new('RGBA', (4, 4), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            alpha = [120, 80, 40][i]
            size = [3, 2, 1][i]
            _rect(draw, 0, 0, size, size, C['dirt1'] + (alpha,))
            self._save_rgba(img, 'particles', f'dust_{i}')

        # Smoke (4x4)
        for i in range(3):
            img = Image.new('RGBA', (4, 4), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            alpha = [100, 60, 30][i]
            _rect(draw, 0, 0, 3, 3, (160, 160, 165, alpha))
            self._save_rgba(img, 'particles', f'smoke_{i}')

        # Spark
        img = Image.new('RGBA', (2, 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _px(draw, 0, 0, (255, 200, 50, 200))
        _px(draw, 1, 0, (255, 230, 100, 150))
        self._save_rgba(img, 'particles', 'spark')

        # Star (2x2)
        img = Image.new('RGBA', (2, 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _px(draw, 0, 0, (255, 255, 230, 200))
        _px(draw, 1, 0, (255, 255, 230, 120))
        self._save_rgba(img, 'particles', 'star')

        # Grain particle
        img = Image.new('RGBA', (2, 3), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _px(draw, 0, 0, C['wheat_gold'] + (200,))
        _px(draw, 0, 1, C['wheat_gold'] + (200,))
        _px(draw, 0, 2, C['wheat_stalk'] + (180,))
        self._save_rgba(img, 'particles', 'grain')

    # ========== ATTACHMENTS ==========

    def generate_attachments(self):
        """Generate equipment attachment sprites."""
        logger.info("  Generating attachments...")

        # Plow (32x16)
        img = Image.new('RGBA', (32, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 0, 4, 4, 2, C['metal_dark'])  # hitch
        _rect(draw, 4, 2, 20, 4, C['metal'])  # beam
        # Plow blades
        for i in range(3):
            bx = 8 + i * 8
            _rect(draw, bx, 6, 6, 8, C['metal'])
            _rect(draw, bx, 6, 6, 1, C['metal_dark'])
            # Curved blade
            _rect(draw, bx + 4, 8, 2, 6, C['metal_light'])
        self._save_rgba(img, 'environment', 'plow')

        # Seeder (32x12)
        img = Image.new('RGBA', (32, 12), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 0, 4, 4, 2, C['metal_dark'])  # hitch
        _rect(draw, 4, 2, 24, 6, C['tractor_red'])  # hopper
        _rect(draw, 4, 2, 24, 1, C['tractor_red_dark'])
        # Seed tubes
        for i in range(4):
            _line_v(draw, 8 + i * 6, 8, 4, C['metal_dark'])
        self._save_rgba(img, 'environment', 'seeder')

        # Trailer (48x20)
        img = Image.new('RGBA', (48, 20), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        _rect(draw, 0, 6, 4, 2, C['metal_dark'])  # hitch
        _rect(draw, 4, 2, 40, 14, C['metal'])  # bed
        _rect(draw, 4, 2, 40, 2, C['metal_dark'])  # rim
        _rect(draw, 4, 2, 1, 14, C['metal_dark'])
        _rect(draw, 43, 2, 1, 14, C['metal_dark'])
        # Wheels
        self._draw_wheel(draw, 14, 17, 3, 0)
        self._draw_wheel(draw, 34, 17, 3, 0)
        self._save_rgba(img, 'environment', 'trailer')


def generate_all_sprites(assets_dir: str):
    """Main entry point for sprite generation."""
    gen = SpriteGenerator(assets_dir)
    gen.generate_all()
    gen.generate_attachments()
    return gen.generated_count
