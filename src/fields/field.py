"""
Field system - manages field tiles, states, and crop growing.
"""
import logging
import random
from enum import Enum, auto
from typing import List, Optional, Dict, Any

logger = logging.getLogger("fields")


class TileState(Enum):
    UNTOUCHED = auto()
    PLOWED = auto()
    CULTIVATED = auto()
    SEEDED = auto()
    GROWING1 = auto()
    GROWING2 = auto()
    GROWING3 = auto()
    MATURE = auto()
    READY = auto()
    HARVESTED = auto()


class FieldTile:
    """A single tile in a field."""
    __slots__ = [
        'state', 'moisture', 'fertility', 'weed', 'pests',
        'health', 'damage', 'quality', 'growth_progress',
        'crop_type', 'x', 'y'
    ]

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.state = TileState.UNTOUCHED
        self.moisture = 0.5
        self.fertility = 0.7 + random.uniform(-0.1, 0.1)
        self.weed = 0.0
        self.pests = 0.0
        self.health = 1.0
        self.damage = 0.0
        self.quality = 0.0
        self.growth_progress = 0.0
        self.crop_type: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'x': self.x, 'y': self.y,
            'state': self.state.name,
            'moisture': round(self.moisture, 3),
            'fertility': round(self.fertility, 3),
            'weed': round(self.weed, 3),
            'pests': round(self.pests, 3),
            'health': round(self.health, 3),
            'damage': round(self.damage, 3),
            'quality': round(self.quality, 3),
            'growth_progress': round(self.growth_progress, 3),
            'crop_type': self.crop_type,
        }

    @staticmethod
    def from_dict(data: dict) -> 'FieldTile':
        t = FieldTile(data['x'], data['y'])
        t.state = TileState[data.get('state', 'UNTOUCHED')]
        t.moisture = data.get('moisture', 0.5)
        t.fertility = data.get('fertility', 0.7)
        t.weed = data.get('weed', 0.0)
        t.pests = data.get('pests', 0.0)
        t.health = data.get('health', 1.0)
        t.damage = data.get('damage', 0.0)
        t.quality = data.get('quality', 0.0)
        t.growth_progress = data.get('growth_progress', 0.0)
        t.crop_type = data.get('crop_type')
        return t


class Field:
    """A field consisting of a grid of tiles."""

    def __init__(self, field_id: int, x: int, y: int, width: int = 20, height: int = 5,
                 crop_type: str = "wheat"):
        self.field_id = field_id
        self.x = x  # World position
        self.y = y
        self.width = width
        self.height = height
        self.crop_type = crop_type
        self.tiles: List[List[FieldTile]] = []

        # Initialize tiles
        for row in range(height):
            tile_row = []
            for col in range(width):
                tile_row.append(FieldTile(col, row))
            self.tiles.append(tile_row)

        # Track what row/col is being processed
        self.current_work_row = 0
        self.current_work_col = 0
        self.work_direction = 1  # 1=right, -1=left

    def get_tile(self, col: int, row: int) -> Optional[FieldTile]:
        if 0 <= row < self.height and 0 <= col < self.width:
            return self.tiles[row][col]
        return None

    def get_next_work_tile(self, target_state: TileState) -> Optional[FieldTile]:
        """Get next tile that needs work (e.g., next unplowed tile)."""
        for row in range(self.height):
            cols = range(self.width) if row % 2 == 0 else range(self.width - 1, -1, -1)
            for col in cols:
                tile = self.tiles[row][col]
                if tile.state == target_state:
                    return tile
        return None

    def count_tiles_in_state(self, state: TileState) -> int:
        count = 0
        for row in self.tiles:
            for tile in row:
                if tile.state == state:
                    count += 1
        return count

    def all_tiles_in_state(self, state: TileState) -> bool:
        return self.count_tiles_in_state(state) == self.width * self.height

    @property
    def total_tiles(self) -> int:
        return self.width * self.height

    @property
    def average_growth(self) -> float:
        total = 0
        count = 0
        for row in self.tiles:
            for tile in row:
                if tile.crop_type:
                    total += tile.growth_progress
                    count += 1
        return total / count if count > 0 else 0.0

    @property
    def is_ready_for_harvest(self) -> bool:
        ready = self.count_tiles_in_state(TileState.READY)
        return ready >= self.total_tiles * 0.8  # 80% ready = field ready

    @property
    def needs_plowing(self) -> bool:
        return self.count_tiles_in_state(TileState.UNTOUCHED) > 0 or \
               self.count_tiles_in_state(TileState.HARVESTED) > 0

    @property
    def needs_cultivating(self) -> bool:
        return self.all_tiles_in_state(TileState.PLOWED)

    @property
    def needs_seeding(self) -> bool:
        return self.all_tiles_in_state(TileState.CULTIVATED)

    @property
    def is_growing(self) -> bool:
        growing_states = {TileState.SEEDED, TileState.GROWING1, TileState.GROWING2,
                         TileState.GROWING3, TileState.MATURE}
        for row in self.tiles:
            for tile in row:
                if tile.state in growing_states:
                    return True
        return False

    def update_growth(self, dt: float, weather_modifier: float = 1.0):
        """Update crop growth for all tiles."""
        # Growth rate: full cycle in ~18 minutes real time
        # Growth phases: SEEDED -> GROWING1 -> GROWING2 -> GROWING3 -> MATURE -> READY
        # Each phase = 20% of total growth
        # Total growth = 1080 seconds (18 min) at modifier 1.0
        growth_rate = dt / 1080.0 * weather_modifier

        for row in self.tiles:
            for tile in row:
                if tile.crop_type and tile.state in (
                    TileState.SEEDED, TileState.GROWING1, TileState.GROWING2,
                    TileState.GROWING3, TileState.MATURE
                ):
                    # Apply growth
                    modifier = tile.fertility * tile.health
                    if tile.moisture < 0.2:
                        modifier *= 0.5
                    elif tile.moisture > 0.8:
                        modifier *= 0.9

                    tile.growth_progress += growth_rate * modifier
                    tile.growth_progress = min(tile.growth_progress, 1.0)

                    # Update quality
                    tile.quality = (
                        tile.fertility * 0.3 +
                        min(tile.moisture, 0.7) / 0.7 * 0.3 +
                        tile.health * 0.4
                    ) * 100

                    # Slow moisture drain
                    tile.moisture = max(0, tile.moisture - dt * 0.0002)

                    # Slow weed/pest growth
                    tile.weed = min(1.0, tile.weed + dt * 0.00005)
                    if tile.weed > 0.5:
                        tile.health = max(0.3, tile.health - dt * 0.0001)

                    # Update state based on progress
                    if tile.growth_progress >= 1.0:
                        tile.state = TileState.READY
                    elif tile.growth_progress >= 0.8:
                        tile.state = TileState.MATURE
                    elif tile.growth_progress >= 0.6:
                        tile.state = TileState.GROWING3
                    elif tile.growth_progress >= 0.4:
                        tile.state = TileState.GROWING2
                    elif tile.growth_progress >= 0.2:
                        tile.state = TileState.GROWING1

    def apply_rain(self, dt: float, intensity: float = 1.0):
        """Apply rain to all tiles."""
        for row in self.tiles:
            for tile in row:
                tile.moisture = min(1.0, tile.moisture + dt * 0.001 * intensity)

    def apply_heat(self, dt: float, intensity: float = 1.0):
        """Apply heat effect."""
        for row in self.tiles:
            for tile in row:
                tile.moisture = max(0, tile.moisture - dt * 0.0005 * intensity)
                if tile.moisture < 0.1 and tile.crop_type:
                    tile.health = max(0.3, tile.health - dt * 0.0002)

    def apply_hail_damage(self, severity: float = 0.3):
        """Apply hail damage to crops."""
        for row in self.tiles:
            for tile in row:
                if tile.crop_type and random.random() < severity:
                    tile.damage += random.uniform(0.1, 0.3)
                    tile.health = max(0.2, tile.health - tile.damage * 0.5)

    def reset_after_harvest(self):
        """Reset field after harvest for next cycle."""
        for row in self.tiles:
            for tile in row:
                tile.state = TileState.HARVESTED
                tile.crop_type = None
                tile.growth_progress = 0.0
                tile.quality = 0.0
                tile.damage = 0.0
                tile.health = 1.0
                tile.weed = min(0.3, tile.weed)

    def to_dict(self) -> dict:
        return {
            'field_id': self.field_id,
            'x': self.x, 'y': self.y,
            'width': self.width, 'height': self.height,
            'crop_type': self.crop_type,
            'tiles': [[t.to_dict() for t in row] for row in self.tiles],
        }

    @staticmethod
    def from_dict(data: dict) -> 'Field':
        f = Field(data['field_id'], data['x'], data['y'],
                  data['width'], data['height'], data.get('crop_type', 'wheat'))
        f.tiles = []
        for row_data in data.get('tiles', []):
            row = [FieldTile.from_dict(td) for td in row_data]
            f.tiles.append(row)
        return f
