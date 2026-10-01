"""
Worker entity system - farm workers with AI, skills, and professions.
"""
import logging
import random
import math
from enum import Enum, auto
from typing import Optional, Dict, Any, List

logger = logging.getLogger("workers")

# Name pools
FIRST_NAMES = [
    "Ivan", "Petr", "Alexei", "Dmitri", "Nikolai", "Sergei", "Viktor",
    "Andrei", "Boris", "Mikhail", "Anna", "Elena", "Olga", "Maria", "Natalia",
    "James", "John", "Robert", "Tom", "William", "Sarah", "Emma", "Kate",
]


class Profession(Enum):
    FARM_WORKER = auto()
    TRACTOR_DRIVER = auto()
    COMBINE_OPERATOR = auto()
    AGRONOMIST = auto()
    MECHANIC = auto()
    TRUCK_DRIVER = auto()


class WorkerState(Enum):
    IDLE = auto()
    WALKING = auto()
    WORKING = auto()
    DRIVING = auto()
    INSPECTING = auto()
    REPAIRING = auto()
    CARRYING = auto()
    RESTING = auto()
    ENTERING_VEHICLE = auto()
    EXITING_VEHICLE = auto()


class TaskType(Enum):
    NONE = auto()
    PLOW_FIELD = auto()
    CULTIVATE_FIELD = auto()
    SEED_FIELD = auto()
    INSPECT_CROP = auto()
    FERTILIZE_FIELD = auto()
    REPAIR_VEHICLE = auto()
    HARVEST_FIELD = auto()
    TRANSPORT_CROP = auto()
    REFUEL_VEHICLE = auto()
    REST = auto()


TASK_PRIORITY = {
    TaskType.REPAIR_VEHICLE: 1,
    TaskType.HARVEST_FIELD: 2,
    TaskType.INSPECT_CROP: 3,
    TaskType.SEED_FIELD: 4,
    TaskType.CULTIVATE_FIELD: 5,
    TaskType.PLOW_FIELD: 6,
    TaskType.TRANSPORT_CROP: 7,
    TaskType.REFUEL_VEHICLE: 8,
    TaskType.FERTILIZE_FIELD: 9,
    TaskType.REST: 10,
}


class WorkerTrait(Enum):
    HARD_WORKER = auto()
    CAREFUL = auto()
    MECHANIC_TALENT = auto()
    FAST_DRIVER = auto()
    AGRONOMY_TALENT = auto()
    FUEL_SAVER = auto()
    SLOW_LEARNER = auto()


TRAIT_EFFECTS = {
    WorkerTrait.HARD_WORKER: {'work_speed': 1.2, 'stamina_drain': 1.3},
    WorkerTrait.CAREFUL: {'work_speed': 0.9, 'quality_bonus': 1.15},
    WorkerTrait.MECHANIC_TALENT: {'repair_speed': 1.5},
    WorkerTrait.FAST_DRIVER: {'drive_speed': 1.3},
    WorkerTrait.AGRONOMY_TALENT: {'inspect_bonus': 1.4},
    WorkerTrait.FUEL_SAVER: {'fuel_efficiency': 0.8},
    WorkerTrait.SLOW_LEARNER: {'xp_rate': 0.7},
}


class Worker:
    """A farm worker entity."""

    _next_id = 1

    def __init__(self, profession: Profession = Profession.FARM_WORKER):
        self.id = Worker._next_id
        Worker._next_id += 1

        self.name = random.choice(FIRST_NAMES)
        self.profession = profession
        self.level = 1
        self.experience = 0
        self.xp_to_next = 100

        # Skills (0-100)
        self.driving = random.randint(10, 40)
        self.agronomy = random.randint(10, 40)
        self.repair = random.randint(10, 40)
        self.harvesting = random.randint(10, 40)
        self.stamina_max = random.randint(80, 100)

        # Apply profession bonuses
        self._apply_profession_bonus()

        # Traits (1-2 random)
        self.traits: List[WorkerTrait] = []
        all_traits = list(WorkerTrait)
        num_traits = random.randint(1, 2)
        self.traits = random.sample(all_traits, num_traits)

        # State
        self.energy = 100.0
        self.mood = 80.0
        self.state = WorkerState.IDLE
        self.current_task = TaskType.NONE

        # Position
        self.x = 0.0
        self.y = 0.0
        self.target_x: Optional[float] = None
        self.target_y: Optional[float] = None
        self.direction = 1  # 1=right, -1=left
        self.moving = False
        self.walk_speed = 30.0

        # Animation
        self.anim_frame = 0
        self.anim_timer = 0.0
        self.sprite_variant = random.choice(['worker1', 'worker2'])

        # Work reference
        self.assigned_vehicle_id: Optional[int] = None
        self.assigned_field_id: Optional[int] = None
        self.work_timer = 0.0

        # Salary
        self.salary = 50 + profession.value * 20

    def _apply_profession_bonus(self):
        """Apply profession-specific skill bonuses."""
        bonuses = {
            Profession.FARM_WORKER: {},
            Profession.TRACTOR_DRIVER: {'driving': 30},
            Profession.COMBINE_OPERATOR: {'driving': 20, 'harvesting': 20},
            Profession.AGRONOMIST: {'agronomy': 40},
            Profession.MECHANIC: {'repair': 40},
            Profession.TRUCK_DRIVER: {'driving': 35},
        }
        for skill, bonus in bonuses.get(self.profession, {}).items():
            setattr(self, skill, min(100, getattr(self, skill) + bonus))

    def update(self, dt: float):
        """Update worker state and position."""
        # Movement
        if self.target_x is not None:
            dx = self.target_x - self.x
            dist = abs(dx)
            move_speed = self.walk_speed * dt

            if dist > 2:
                self.direction = 1 if dx > 0 else -1
                self.x += self.direction * min(move_speed, dist)
                self.moving = True
                self.state = WorkerState.WALKING
            else:
                self.x = self.target_x
                self.target_x = None
                self.moving = False
                if self.state == WorkerState.WALKING:
                    self.state = WorkerState.IDLE

        # Animation
        if self.moving:
            self.anim_timer += dt
            if self.anim_timer >= 0.2:
                self.anim_timer -= 0.2
                self.anim_frame = (self.anim_frame + 1) % 4
        else:
            self.anim_frame = 0

        # Energy drain
        if self.state in (WorkerState.WORKING, WorkerState.DRIVING,
                          WorkerState.REPAIRING, WorkerState.CARRYING):
            drain = dt * 0.02
            if WorkerTrait.HARD_WORKER in self.traits:
                drain *= 1.3
            self.energy = max(0, self.energy - drain)

        # Rest recovery
        if self.state == WorkerState.RESTING:
            self.energy = min(100, self.energy + dt * 0.05)
            self.mood = min(100, self.mood + dt * 0.02)
            if self.energy >= 90:
                self.state = WorkerState.IDLE
                self.current_task = TaskType.NONE

        # Need rest check
        if self.energy < 10 and self.state != WorkerState.RESTING:
            self.state = WorkerState.RESTING
            self.current_task = TaskType.REST
            logger.info(f"Worker {self.name} needs rest (energy: {self.energy:.0f})")

    def gain_xp(self, amount: float):
        """Gain experience points."""
        if WorkerTrait.SLOW_LEARNER in self.traits:
            amount *= 0.7
        self.experience += amount
        while self.experience >= self.xp_to_next and self.level < 20:
            self.experience -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.5)
            # Improve skills on level up
            self.driving = min(100, self.driving + random.randint(1, 3))
            self.agronomy = min(100, self.agronomy + random.randint(1, 3))
            self.repair = min(100, self.repair + random.randint(1, 3))
            self.harvesting = min(100, self.harvesting + random.randint(1, 3))
            logger.info(f"Worker {self.name} reached level {self.level}!")

    def move_to(self, x: float, y: float = None):
        """Set movement target."""
        self.target_x = x
        if y is not None:
            self.target_y = y

    @property
    def is_available(self) -> bool:
        return (self.state == WorkerState.IDLE and
                self.energy > 20 and
                self.current_task == TaskType.NONE)

    @property
    def work_modifier(self) -> float:
        """Overall work efficiency modifier."""
        mod = 0.5 + (self.level / 20) * 0.5
        if WorkerTrait.HARD_WORKER in self.traits:
            mod *= 1.2
        if self.energy < 30:
            mod *= 0.5
        return mod

    @property
    def sprite_key(self) -> str:
        d = 'right' if self.direction > 0 else 'left'
        if self.moving:
            return f"workers/{self.sprite_variant}/{d}_{self.anim_frame}.png"
        return f"workers/{self.sprite_variant}/idle.png"

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'profession': self.profession.name,
            'level': self.level,
            'experience': self.experience,
            'xp_to_next': self.xp_to_next,
            'driving': self.driving,
            'agronomy': self.agronomy,
            'repair': self.repair,
            'harvesting': self.harvesting,
            'stamina_max': self.stamina_max,
            'traits': [t.name for t in self.traits],
            'energy': round(self.energy, 1),
            'mood': round(self.mood, 1),
            'state': self.state.name,
            'current_task': self.current_task.name,
            'x': round(self.x, 1),
            'y': round(self.y, 1),
            'direction': self.direction,
            'sprite_variant': self.sprite_variant,
            'salary': self.salary,
            'assigned_vehicle_id': self.assigned_vehicle_id,
            'assigned_field_id': self.assigned_field_id,
        }

    @staticmethod
    def from_dict(data: dict) -> 'Worker':
        w = Worker(Profession[data.get('profession', 'FARM_WORKER')])
        w.id = data.get('id', w.id)
        w.name = data.get('name', w.name)
        w.level = data.get('level', 1)
        w.experience = data.get('experience', 0)
        w.xp_to_next = data.get('xp_to_next', 100)
        w.driving = data.get('driving', 20)
        w.agronomy = data.get('agronomy', 20)
        w.repair = data.get('repair', 20)
        w.harvesting = data.get('harvesting', 20)
        w.stamina_max = data.get('stamina_max', 100)
        w.traits = [WorkerTrait[t] for t in data.get('traits', [])]
        w.energy = data.get('energy', 100)
        w.mood = data.get('mood', 80)
        w.state = WorkerState[data.get('state', 'IDLE')]
        w.current_task = TaskType[data.get('current_task', 'NONE')]
        w.x = data.get('x', 0)
        w.y = data.get('y', 0)
        w.direction = data.get('direction', 1)
        w.sprite_variant = data.get('sprite_variant', 'worker1')
        w.salary = data.get('salary', 50)
        w.assigned_vehicle_id = data.get('assigned_vehicle_id')
        w.assigned_field_id = data.get('assigned_field_id')
        Worker._next_id = max(Worker._next_id, w.id + 1)
        return w
