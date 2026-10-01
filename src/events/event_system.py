"""
Event system - random, decorative, positive, and negative events.
"""
import logging
import random
from enum import Enum, auto
from typing import List, Optional, Callable, Dict, Any

logger = logging.getLogger("events")


class EventCategory(Enum):
    NEGATIVE = auto()
    POSITIVE = auto()
    DECORATIVE = auto()


class GameEvent:
    """A game event with effects and duration."""

    def __init__(self, event_id: str, name: str, category: EventCategory,
                 duration: float = 30, description: str = ""):
        self.event_id = event_id
        self.name = name
        self.category = category
        self.duration = duration
        self.remaining = duration
        self.description = description
        self.active = True
        self.data: Dict[str, Any] = {}

    def update(self, dt: float) -> bool:
        """Update event timer. Returns False when expired."""
        self.remaining -= dt
        if self.remaining <= 0:
            self.active = False
            return False
        return True


# Event definitions
EVENT_DEFINITIONS = {
    # Negative events
    "tractor_breakdown": {
        "name": "Tractor Breakdown",
        "category": EventCategory.NEGATIVE,
        "duration": 60,
        "chance": 0.003,
        "min_interval": 300,
    },
    "flat_tire": {
        "name": "Flat Tire",
        "category": EventCategory.NEGATIVE,
        "duration": 45,
        "chance": 0.002,
        "min_interval": 240,
    },
    "pest_outbreak": {
        "name": "Pest Outbreak",
        "category": EventCategory.NEGATIVE,
        "duration": 120,
        "chance": 0.001,
        "min_interval": 600,
    },
    "weed_outbreak": {
        "name": "Weed Outbreak",
        "category": EventCategory.NEGATIVE,
        "duration": 90,
        "chance": 0.001,
        "min_interval": 500,
    },
    "worker_tired": {
        "name": "Worker Exhausted",
        "category": EventCategory.NEGATIVE,
        "duration": 60,
        "chance": 0.002,
        "min_interval": 180,
    },
    "fuel_shortage": {
        "name": "Fuel Shortage",
        "category": EventCategory.NEGATIVE,
        "duration": 90,
        "chance": 0.001,
        "min_interval": 600,
    },

    # Positive events
    "perfect_weather": {
        "name": "Perfect Weather",
        "category": EventCategory.POSITIVE,
        "duration": 180,
        "chance": 0.002,
        "min_interval": 400,
    },
    "high_market_price": {
        "name": "Market Prices Up!",
        "category": EventCategory.POSITIVE,
        "duration": 120,
        "chance": 0.002,
        "min_interval": 300,
    },
    "worker_inspiration": {
        "name": "Worker Inspired!",
        "category": EventCategory.POSITIVE,
        "duration": 90,
        "chance": 0.002,
        "min_interval": 300,
    },
    "bumper_crop": {
        "name": "Bumper Crop!",
        "category": EventCategory.POSITIVE,
        "duration": 60,
        "chance": 0.001,
        "min_interval": 600,
    },

    # Decorative events (no gameplay impact)
    "dog_chases_tractor": {
        "name": "Dog Chasing Tractor",
        "category": EventCategory.DECORATIVE,
        "duration": 15,
        "chance": 0.005,
        "min_interval": 120,
    },
    "birds_follow_plow": {
        "name": "Birds Following Plow",
        "category": EventCategory.DECORATIVE,
        "duration": 30,
        "chance": 0.004,
        "min_interval": 60,
    },
    "cat_on_roof": {
        "name": "Cat on the Roof",
        "category": EventCategory.DECORATIVE,
        "duration": 60,
        "chance": 0.003,
        "min_interval": 120,
    },
    "rabbit_crosses": {
        "name": "Rabbit Crossing",
        "category": EventCategory.DECORATIVE,
        "duration": 8,
        "chance": 0.003,
        "min_interval": 180,
    },
    "worker_drinks_tea": {
        "name": "Tea Break",
        "category": EventCategory.DECORATIVE,
        "duration": 20,
        "chance": 0.004,
        "min_interval": 120,
    },
    "airplane": {
        "name": "Airplane Flyby",
        "category": EventCategory.DECORATIVE,
        "duration": 10,
        "chance": 0.002,
        "min_interval": 300,
    },
    "rainbow": {
        "name": "Rainbow",
        "category": EventCategory.DECORATIVE,
        "duration": 60,
        "chance": 0.001,  # Only after rain
        "min_interval": 600,
    },
    "shooting_star": {
        "name": "Shooting Star",
        "category": EventCategory.DECORATIVE,
        "duration": 3,
        "chance": 0.003,
        "min_interval": 300,
    },
}


class EventSystem:
    """Manages random game events."""

    def __init__(self):
        self.active_events: List[GameEvent] = []
        self.event_log: List[Dict[str, Any]] = []
        self._cooldowns: Dict[str, float] = {}
        self._check_timer = 0.0
        self._check_interval = 5.0  # Check every 5 seconds
        self.total_events = 0

    def update(self, dt: float, is_raining: bool = False, is_night: bool = False):
        """Update active events and check for new ones."""
        # Update active events
        expired = []
        for event in self.active_events:
            if not event.update(dt):
                expired.append(event)
                logger.info(f"Event ended: {event.name}")

        for event in expired:
            self.active_events.remove(event)

        # Update cooldowns
        for eid in list(self._cooldowns.keys()):
            self._cooldowns[eid] -= dt
            if self._cooldowns[eid] <= 0:
                del self._cooldowns[eid]

        # Check for new events
        self._check_timer -= dt
        if self._check_timer <= 0:
            self._check_timer = self._check_interval
            self._try_spawn_event(is_raining, is_night)

    def _try_spawn_event(self, is_raining: bool, is_night: bool):
        """Try to spawn a random event."""
        for event_id, definition in EVENT_DEFINITIONS.items():
            # Skip if on cooldown
            if event_id in self._cooldowns:
                continue

            # Skip already active
            if any(e.event_id == event_id for e in self.active_events):
                continue

            # Special conditions
            if event_id == "rainbow" and not is_raining:
                continue
            if event_id == "shooting_star" and not is_night:
                continue

            # Roll chance
            if random.random() < definition['chance']:
                self._spawn_event(event_id, definition)
                break  # Only one event per check

    def _spawn_event(self, event_id: str, definition: dict):
        """Spawn a new event."""
        event = GameEvent(
            event_id=event_id,
            name=definition['name'],
            category=definition['category'],
            duration=definition['duration'],
        )
        self.active_events.append(event)
        self._cooldowns[event_id] = definition.get('min_interval', 300)
        self.total_events += 1

        self.event_log.append({
            'id': event_id,
            'name': definition['name'],
            'category': definition['category'].name,
        })
        if len(self.event_log) > 50:
            self.event_log = self.event_log[-50:]

        logger.info(f"Event spawned: {definition['name']} "
                    f"({definition['category'].name}, {definition['duration']}s)")

    def has_event(self, event_id: str) -> bool:
        return any(e.event_id == event_id and e.active for e in self.active_events)

    def get_active_of_category(self, category: EventCategory) -> List[GameEvent]:
        return [e for e in self.active_events
                if e.category == category and e.active]

    def to_dict(self) -> dict:
        return {
            'total_events': self.total_events,
            'event_log': self.event_log[-20:],
        }

    @staticmethod
    def from_dict(data: dict) -> 'EventSystem':
        es = EventSystem()
        es.total_events = data.get('total_events', 0)
        es.event_log = data.get('event_log', [])
        return es
