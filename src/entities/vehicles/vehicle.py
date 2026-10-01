"""
Vehicle entity system - tractors, combines, trucks.
"""
import logging
import random
import math
from enum import Enum, auto
from typing import Optional, Dict, Any, List

logger = logging.getLogger("vehicles")


class VehicleType(Enum):
    SMALL_TRACTOR = auto()
    MEDIUM_TRACTOR = auto()
    HEAVY_TRACTOR = auto()
    MODERN_TRACTOR = auto()
    SMALL_COMBINE = auto()
    MEDIUM_COMBINE = auto()
    LARGE_COMBINE = auto()
    FARM_TRUCK = auto()
    GRAIN_TRUCK = auto()
    LARGE_GRAIN_TRUCK = auto()


class VehicleState(Enum):
    IDLE = auto()
    DRIVING = auto()
    WORKING = auto()  # Plowing, seeding, etc.
    HARVESTING = auto()
    LOADING = auto()
    UNLOADING = auto()
    REFUELING = auto()
    BROKEN = auto()
    REPAIRING = auto()
    PARKED = auto()


class AttachmentType(Enum):
    NONE = auto()
    PLOW = auto()
    CULTIVATOR = auto()
    SEEDER = auto()
    FERTILIZER = auto()
    SPRAYER = auto()
    TRAILER = auto()


VEHICLE_DATA = {
    VehicleType.SMALL_TRACTOR: {
        'name': 'Small Tractor',
        'speed': 40, 'work_speed': 0.8,
        'fuel_capacity': 80, 'fuel_consumption': 0.03,
        'reliability': 0.6, 'power': 50,
        'price': 2000, 'repair_cost': 200,
        'sprite_folder': 'tractors/small_tractor',
        'size': (48, 32),
    },
    VehicleType.MEDIUM_TRACTOR: {
        'name': 'Medium Tractor',
        'speed': 55, 'work_speed': 1.0,
        'fuel_capacity': 120, 'fuel_consumption': 0.04,
        'reliability': 0.8, 'power': 80,
        'price': 5000, 'repair_cost': 400,
        'sprite_folder': 'tractors/medium_tractor',
        'size': (48, 32),
    },
    VehicleType.SMALL_COMBINE: {
        'name': 'Small Combine',
        'speed': 30, 'work_speed': 0.7,
        'fuel_capacity': 150, 'fuel_consumption': 0.06,
        'reliability': 0.7, 'power': 100,
        'price': 15000, 'repair_cost': 1500,
        'sprite_folder': 'combines/small_combine',
        'size': (96, 48),
    },
    VehicleType.FARM_TRUCK: {
        'name': 'Farm Truck',
        'speed': 60, 'work_speed': 1.0,
        'fuel_capacity': 100, 'fuel_consumption': 0.035,
        'reliability': 0.85, 'power': 70,
        'price': 3000, 'repair_cost': 300,
        'sprite_folder': 'trucks/farm_truck',
        'size': (64, 32),
    },
}


class Vehicle:
    """A vehicle entity with position, state, and attributes."""

    _next_id = 1

    def __init__(self, vehicle_type: VehicleType, x: float = 0, y: float = 0):
        self.id = Vehicle._next_id
        Vehicle._next_id += 1

        self.vehicle_type = vehicle_type
        self.data = VEHICLE_DATA.get(vehicle_type, VEHICLE_DATA[VehicleType.SMALL_TRACTOR])

        # Position and movement
        self.x = x
        self.y = y
        self.target_x: Optional[float] = None
        self.target_y: Optional[float] = None
        self.direction = 1  # 1=right, -1=left
        self.moving = False

        # State
        self.state = VehicleState.PARKED
        self.attachment = AttachmentType.NONE

        # Stats
        self.speed = self.data['speed']
        self.work_speed = self.data['work_speed']
        self.fuel = self.data['fuel_capacity']
        self.fuel_capacity = self.data['fuel_capacity']
        self.fuel_consumption = self.data['fuel_consumption']
        self.condition = 100.0  # 0-100%
        self.reliability = self.data['reliability']

        # Animation
        self.anim_frame = 0
        self.anim_timer = 0.0
        self.anim_speed = 0.15
        self.smoke_timer = 0.0
        self.dust_particles: List[Dict] = []

        # Work
        self.current_field_id: Optional[int] = None
        self.work_progress = 0.0
        self.cargo = 0.0  # For trucks/trailers
        self.cargo_capacity = 500.0
        self.cargo_type: Optional[str] = None

        # Driver
        self.driver_id: Optional[int] = None

    def update(self, dt: float):
        """Update vehicle state and position."""
        if self.state == VehicleState.BROKEN:
            return

        # Movement
        if self.target_x is not None and self.state in (VehicleState.DRIVING, VehicleState.WORKING):
            dx = self.target_x - self.x
            dist = abs(dx)
            move_speed = self.speed * dt * self._condition_modifier

            if dist > 2:
                self.direction = 1 if dx > 0 else -1
                self.x += self.direction * min(move_speed, dist)
                self.moving = True

                # Fuel consumption
                self.fuel -= self.fuel_consumption * dt
                if self.fuel <= 0:
                    self.fuel = 0
                    self.state = VehicleState.IDLE
                    self.moving = False
                    logger.info(f"Vehicle {self.id} out of fuel")
            else:
                self.x = self.target_x
                self.target_x = None
                self.moving = False
                if self.state == VehicleState.DRIVING:
                    self.state = VehicleState.IDLE

        # Animation
        if self.moving or self.state == VehicleState.WORKING:
            self.anim_timer += dt
            if self.anim_timer >= self.anim_speed:
                self.anim_timer -= self.anim_speed
                self.anim_frame = (self.anim_frame + 1) % 4

            # Dust particles when moving
            self.smoke_timer += dt
            if self.smoke_timer >= 0.3:
                self.smoke_timer = 0
                if self.moving:
                    self.dust_particles.append({
                        'x': self.x + (0 if self.direction > 0 else self.data['size'][0]),
                        'y': self.y + self.data['size'][1] - 4,
                        'life': 1.0,
                        'vx': -self.direction * random.uniform(5, 15),
                        'vy': random.uniform(-10, -5),
                    })

        # Update dust particles
        alive = []
        for p in self.dust_particles:
            p['life'] -= dt * 2
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            if p['life'] > 0:
                alive.append(p)
        self.dust_particles = alive[:20]  # Pool limit

        # Random breakdown check
        if self.state == VehicleState.WORKING and random.random() < 0.00005 * (1 - self.reliability):
            if self.condition < 40:
                self.state = VehicleState.BROKEN
                logger.info(f"Vehicle {self.id} broke down! Condition: {self.condition:.0f}%")

        # Wear
        if self.state in (VehicleState.WORKING, VehicleState.DRIVING):
            self.condition = max(0, self.condition - dt * 0.002 * (2 - self.reliability))

    @property
    def _condition_modifier(self) -> float:
        if self.condition >= 70:
            return 1.0
        elif self.condition >= 40:
            return 0.7
        elif self.condition >= 20:
            return 0.4
        return 0.2

    def move_to(self, x: float, y: float = None):
        """Set movement target."""
        self.target_x = x
        if y is not None:
            self.target_y = y
        self.state = VehicleState.DRIVING

    def start_work(self, field_id: int):
        """Start working on a field."""
        self.state = VehicleState.WORKING
        self.current_field_id = field_id
        self.work_progress = 0.0

    def stop(self):
        """Stop and park."""
        self.state = VehicleState.PARKED
        self.moving = False
        self.target_x = None

    def repair(self, amount: float = 30):
        """Repair vehicle."""
        self.condition = min(100, self.condition + amount)
        if self.state == VehicleState.BROKEN:
            self.state = VehicleState.IDLE

    def refuel(self, amount: float = None):
        """Refuel vehicle."""
        if amount is None:
            amount = self.fuel_capacity - self.fuel
        self.fuel = min(self.fuel_capacity, self.fuel + amount)

    @property
    def needs_fuel(self) -> bool:
        return self.fuel < self.fuel_capacity * 0.2

    @property
    def needs_repair(self) -> bool:
        return self.condition < 40

    @property
    def sprite_key(self) -> str:
        """Get current sprite key."""
        d = 'right' if self.direction > 0 else 'left'
        folder = self.data['sprite_folder']
        return f"{folder}/{d}_{self.anim_frame}.png"

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'type': self.vehicle_type.name,
            'x': round(self.x, 1), 'y': round(self.y, 1),
            'direction': self.direction,
            'state': self.state.name,
            'attachment': self.attachment.name,
            'fuel': round(self.fuel, 1),
            'condition': round(self.condition, 1),
            'cargo': round(self.cargo, 1),
            'cargo_type': self.cargo_type,
            'driver_id': self.driver_id,
        }

    @staticmethod
    def from_dict(data: dict) -> 'Vehicle':
        vtype = VehicleType[data.get('type', 'SMALL_TRACTOR')]
        v = Vehicle(vtype, data.get('x', 0), data.get('y', 0))
        v.id = data.get('id', v.id)
        v.direction = data.get('direction', 1)
        v.state = VehicleState[data.get('state', 'PARKED')]
        v.attachment = AttachmentType[data.get('attachment', 'NONE')]
        v.fuel = data.get('fuel', v.fuel_capacity)
        v.condition = data.get('condition', 100)
        v.cargo = data.get('cargo', 0)
        v.cargo_type = data.get('cargo_type')
        v.driver_id = data.get('driver_id')
        Vehicle._next_id = max(Vehicle._next_id, v.id + 1)
        return v
