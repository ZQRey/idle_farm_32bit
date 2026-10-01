"""
Farm animals - decorative NPCs (dog, cat).
"""
import logging
import random
import math
from enum import Enum, auto
from typing import Optional, List

logger = logging.getLogger("animals")


class AnimalState(Enum):
    IDLE = auto()
    WALKING = auto()
    RUNNING = auto()
    SLEEPING = auto()
    FOLLOWING = auto()


class FarmAnimal:
    """Base class for farm animals (decorative NPCs)."""

    def __init__(self, animal_type: str, x: float, y: float):
        self.animal_type = animal_type
        self.x = x
        self.y = y
        self.home_x = x
        self.home_y = y
        self.direction = 1
        self.state = AnimalState.IDLE
        self.moving = False

        # Movement
        self.target_x: Optional[float] = None
        self.walk_speed = 20.0
        self.run_speed = 60.0

        # Animation
        self.anim_frame = 0
        self.anim_timer = 0.0

        # Behavior timers
        self.idle_timer = 0.0
        self.idle_duration = random.uniform(5, 15)
        self.action_timer = 0.0

        # Following
        self.follow_target_x: Optional[float] = None

    def update(self, dt: float, is_raining: bool = False, is_night: bool = False):
        """Update animal behavior."""
        raise NotImplementedError


class FarmDog(FarmAnimal):
    """Farm dog NPC."""

    def __init__(self, x: float, y: float):
        super().__init__("dog", x, y)
        self.walk_speed = 25.0
        self.run_speed = 70.0

    def update(self, dt: float, is_raining: bool = False, is_night: bool = False):
        """Update dog behavior."""
        # Movement
        if self.target_x is not None:
            dx = self.target_x - self.x
            dist = abs(dx)
            speed = self.run_speed if self.state == AnimalState.RUNNING else self.walk_speed

            if dist > 3:
                self.direction = 1 if dx > 0 else -1
                self.x += self.direction * min(speed * dt, dist)
                self.moving = True
            else:
                self.x = self.target_x
                self.target_x = None
                self.moving = False
                self.state = AnimalState.IDLE
                self.idle_timer = 0
                self.idle_duration = random.uniform(3, 10)

        # Animation
        if self.moving:
            self.anim_timer += dt
            anim_speed = 0.15 if self.state != AnimalState.RUNNING else 0.1
            if self.anim_timer >= anim_speed:
                self.anim_timer -= anim_speed
                self.anim_frame = (self.anim_frame + 1) % 4

        # Behavior AI
        if not self.moving:
            self.idle_timer += dt

            if self.idle_timer >= self.idle_duration:
                self.idle_timer = 0

                if is_night and random.random() < 0.7:
                    # Sleep near farmhouse at night
                    self.state = AnimalState.SLEEPING
                    self.idle_duration = random.uniform(30, 60)
                elif is_raining and random.random() < 0.6:
                    # Hide during rain (go home)
                    self.target_x = self.home_x + random.uniform(-20, 20)
                    self.state = AnimalState.RUNNING
                elif random.random() < 0.6:
                    # Wander around
                    wander_range = 150
                    self.target_x = self.home_x + random.uniform(-wander_range, wander_range)
                    self.state = AnimalState.WALKING
                    self.idle_duration = random.uniform(5, 15)
                else:
                    self.idle_duration = random.uniform(5, 12)

    @property
    def sprite_key(self) -> str:
        if self.state == AnimalState.SLEEPING:
            return "animals/dog_sleep.png"
        d = 'right' if self.direction > 0 else 'left'
        if self.moving:
            return f"animals/dog_{d}_{self.anim_frame}.png"
        return f"animals/dog_{d}_0.png"


class FarmCat(FarmAnimal):
    """Farm cat NPC."""

    def __init__(self, x: float, y: float):
        super().__init__("cat", x, y)
        self.walk_speed = 18.0
        self.run_speed = 55.0
        self.on_roof = False

    def update(self, dt: float, is_raining: bool = False, is_night: bool = False):
        """Update cat behavior."""
        # Movement
        if self.target_x is not None and not self.on_roof:
            dx = self.target_x - self.x
            dist = abs(dx)
            speed = self.run_speed if self.state == AnimalState.RUNNING else self.walk_speed

            if dist > 2:
                self.direction = 1 if dx > 0 else -1
                self.x += self.direction * min(speed * dt, dist)
                self.moving = True
            else:
                self.x = self.target_x
                self.target_x = None
                self.moving = False
                self.state = AnimalState.IDLE
                self.idle_timer = 0

        # Animation
        if self.moving:
            self.anim_timer += dt
            if self.anim_timer >= 0.18:
                self.anim_timer -= 0.18
                self.anim_frame = (self.anim_frame + 1) % 4

        # Behavior
        if not self.moving:
            self.idle_timer += dt
            if self.idle_timer >= self.idle_duration:
                self.idle_timer = 0

                if random.random() < 0.3 and not self.on_roof:
                    # Go sit on roof
                    self.on_roof = True
                    self.state = AnimalState.IDLE
                    self.idle_duration = random.uniform(20, 60)
                elif self.on_roof and random.random() < 0.4:
                    # Come down from roof
                    self.on_roof = False
                    self.idle_duration = random.uniform(5, 15)
                elif random.random() < 0.5 and not self.on_roof:
                    # Sleep
                    self.state = AnimalState.SLEEPING
                    self.idle_duration = random.uniform(15, 45)
                elif not self.on_roof:
                    # Wander
                    self.target_x = self.home_x + random.uniform(-100, 100)
                    self.state = AnimalState.WALKING
                    self.idle_duration = random.uniform(8, 20)
                else:
                    self.idle_duration = random.uniform(10, 30)

    @property
    def sprite_key(self) -> str:
        if self.state == AnimalState.SLEEPING:
            return "animals/cat_sleep.png"
        d = 'right' if self.direction > 0 else 'left'
        if self.moving:
            return f"animals/cat_{d}_{self.anim_frame}.png"
        return f"animals/cat_{d}_0.png"
