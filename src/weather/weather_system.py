"""
Weather system for Desktop Idle Farm.
"""
import logging
import random
from enum import Enum, auto
from typing import Optional, Dict

logger = logging.getLogger("weather")


class WeatherType(Enum):
    CLEAR = auto()
    CLOUDY = auto()
    RAIN = auto()
    HEAVY_RAIN = auto()
    STORM = auto()
    HEAT = auto()
    STRONG_WIND = auto()
    HAIL = auto()
    SNOW = auto()
    FOG = auto()


# Weather transition probabilities (from -> to weights)
WEATHER_TRANSITIONS = {
    WeatherType.CLEAR: {
        WeatherType.CLEAR: 60,
        WeatherType.CLOUDY: 25,
        WeatherType.HEAT: 10,
        WeatherType.FOG: 5,
    },
    WeatherType.CLOUDY: {
        WeatherType.CLEAR: 30,
        WeatherType.CLOUDY: 30,
        WeatherType.RAIN: 25,
        WeatherType.STRONG_WIND: 10,
        WeatherType.FOG: 5,
    },
    WeatherType.RAIN: {
        WeatherType.RAIN: 30,
        WeatherType.CLOUDY: 30,
        WeatherType.HEAVY_RAIN: 20,
        WeatherType.CLEAR: 15,
        WeatherType.STORM: 5,
    },
    WeatherType.HEAVY_RAIN: {
        WeatherType.RAIN: 35,
        WeatherType.HEAVY_RAIN: 25,
        WeatherType.STORM: 20,
        WeatherType.CLOUDY: 15,
        WeatherType.HAIL: 5,
    },
    WeatherType.STORM: {
        WeatherType.HEAVY_RAIN: 30,
        WeatherType.RAIN: 30,
        WeatherType.STORM: 15,
        WeatherType.CLOUDY: 15,
        WeatherType.HAIL: 10,
    },
    WeatherType.HEAT: {
        WeatherType.HEAT: 40,
        WeatherType.CLEAR: 40,
        WeatherType.CLOUDY: 15,
        WeatherType.STORM: 5,
    },
    WeatherType.STRONG_WIND: {
        WeatherType.CLOUDY: 35,
        WeatherType.CLEAR: 30,
        WeatherType.STRONG_WIND: 20,
        WeatherType.RAIN: 10,
        WeatherType.STORM: 5,
    },
    WeatherType.HAIL: {
        WeatherType.RAIN: 40,
        WeatherType.CLOUDY: 30,
        WeatherType.CLEAR: 20,
        WeatherType.STORM: 10,
    },
    WeatherType.SNOW: {
        WeatherType.SNOW: 40,
        WeatherType.CLOUDY: 30,
        WeatherType.CLEAR: 20,
        WeatherType.FOG: 10,
    },
    WeatherType.FOG: {
        WeatherType.CLOUDY: 40,
        WeatherType.CLEAR: 35,
        WeatherType.FOG: 15,
        WeatherType.RAIN: 10,
    },
}


class WeatherSystem:
    """Manages weather simulation and effects."""

    def __init__(self):
        self.current = WeatherType.CLEAR
        self.intensity = 0.5  # 0-1
        self.duration = 0.0  # seconds remaining
        self.min_duration = 60  # 1 minute minimum
        self.max_duration = 300  # 5 minutes maximum
        self.transition_timer = 0.0
        self.transition_duration = 5.0  # 5 second transitions

        self._set_random_duration()

        # Visual state
        self.rain_particles: list = []
        self.snow_particles: list = []
        self.cloud_positions: list = []

        # Initialize clouds
        for i in range(3):
            self.cloud_positions.append({
                'x': random.randint(0, 1920),
                'y': random.randint(2, 20),
                'speed': random.uniform(5, 15),
                'type': random.choice(['light', 'dark']),
            })

    def update(self, dt: float, screen_width: int = 1920):
        """Update weather state."""
        self.duration -= dt

        if self.duration <= 0:
            self._transition_weather()

        # Update intensity (slight fluctuation)
        self.intensity += random.uniform(-0.02, 0.02) * dt
        self.intensity = max(0.2, min(1.0, self.intensity))

        # Update cloud positions
        for cloud in self.cloud_positions:
            cloud['x'] += cloud['speed'] * dt
            if cloud['x'] > screen_width + 60:
                cloud['x'] = -60
                cloud['y'] = random.randint(2, 20)

        # Update rain particles
        if self.current in (WeatherType.RAIN, WeatherType.HEAVY_RAIN, WeatherType.STORM):
            self._update_rain(dt, screen_width)

        # Update snow
        if self.current == WeatherType.SNOW:
            self._update_snow(dt, screen_width)

    def _update_rain(self, dt: float, screen_width: int):
        """Update rain particle system."""
        # Spawn new drops
        rate = 5 if self.current == WeatherType.RAIN else 12
        for _ in range(int(rate * dt * 60)):
            if len(self.rain_particles) < 200:
                self.rain_particles.append({
                    'x': random.randint(0, screen_width),
                    'y': random.randint(-20, 0),
                    'speed': random.uniform(200, 350),
                    'length': random.randint(4, 8),
                })

        # Move existing
        alive = []
        for p in self.rain_particles:
            p['y'] += p['speed'] * dt
            p['x'] -= 20 * dt  # slight wind
            if p['y'] < 200:
                alive.append(p)
        self.rain_particles = alive

    def _update_snow(self, dt: float, screen_width: int):
        """Update snow particle system."""
        for _ in range(int(2 * dt * 60)):
            if len(self.snow_particles) < 100:
                self.snow_particles.append({
                    'x': random.randint(0, screen_width),
                    'y': random.randint(-10, 0),
                    'speed': random.uniform(20, 50),
                    'drift': random.uniform(-15, 15),
                })

        alive = []
        for p in self.snow_particles:
            p['y'] += p['speed'] * dt
            p['x'] += p['drift'] * dt
            if p['y'] < 200:
                alive.append(p)
        self.snow_particles = alive

    def _transition_weather(self):
        """Transition to next weather state."""
        transitions = WEATHER_TRANSITIONS.get(self.current, {WeatherType.CLEAR: 100})
        choices = list(transitions.keys())
        weights = list(transitions.values())

        self.current = random.choices(choices, weights=weights, k=1)[0]
        self._set_random_duration()
        self.intensity = random.uniform(0.3, 0.8)

        logger.info(f"Weather changed to: {self.current.name} "
                    f"(duration: {self.duration:.0f}s, intensity: {self.intensity:.2f})")

    def _set_random_duration(self):
        self.duration = random.uniform(self.min_duration, self.max_duration)

    @property
    def moisture_modifier(self) -> float:
        """How much this weather adds moisture."""
        mods = {
            WeatherType.RAIN: 0.3 * self.intensity,
            WeatherType.HEAVY_RAIN: 0.6 * self.intensity,
            WeatherType.STORM: 0.5 * self.intensity,
            WeatherType.SNOW: 0.1,
            WeatherType.HEAT: -0.3 * self.intensity,
            WeatherType.STRONG_WIND: -0.1,
        }
        return mods.get(self.current, 0.0)

    @property
    def work_speed_modifier(self) -> float:
        """How weather affects work speed."""
        mods = {
            WeatherType.CLEAR: 1.0,
            WeatherType.CLOUDY: 1.0,
            WeatherType.RAIN: 0.8,
            WeatherType.HEAVY_RAIN: 0.5,
            WeatherType.STORM: 0.3,
            WeatherType.HEAT: 0.7,
            WeatherType.STRONG_WIND: 0.8,
            WeatherType.HAIL: 0.2,
            WeatherType.SNOW: 0.4,
            WeatherType.FOG: 0.7,
        }
        return mods.get(self.current, 1.0)

    @property
    def growth_modifier(self) -> float:
        """How weather affects crop growth."""
        mods = {
            WeatherType.CLEAR: 1.0,
            WeatherType.CLOUDY: 0.9,
            WeatherType.RAIN: 1.2,
            WeatherType.HEAVY_RAIN: 1.0,
            WeatherType.STORM: 0.6,
            WeatherType.HEAT: 0.7,
            WeatherType.STRONG_WIND: 0.8,
            WeatherType.HAIL: 0.3,
            WeatherType.SNOW: 0.1,
            WeatherType.FOG: 0.8,
        }
        return mods.get(self.current, 1.0)

    @property
    def is_raining(self) -> bool:
        return self.current in (WeatherType.RAIN, WeatherType.HEAVY_RAIN, WeatherType.STORM)

    @property
    def is_dangerous(self) -> bool:
        return self.current in (WeatherType.STORM, WeatherType.HAIL, WeatherType.HEAVY_RAIN)

    @property
    def wind_speed(self) -> float:
        """Normalized wind speed factor (0.5 to 2.5)."""
        if self.current == WeatherType.STRONG_WIND:
            return 2.5
        elif self.current == WeatherType.STORM:
            return 2.0
        elif self.current in (WeatherType.RAIN, WeatherType.HEAVY_RAIN):
            return 1.3
        return 0.8

    def to_dict(self) -> dict:
        return {
            'current': self.current.name,
            'intensity': self.intensity,
            'duration': self.duration,
        }

    @staticmethod
    def from_dict(data: dict) -> 'WeatherSystem':
        ws = WeatherSystem()
        ws.current = WeatherType[data.get('current', 'CLEAR')]
        ws.intensity = data.get('intensity', 0.5)
        ws.duration = data.get('duration', 120)
        return ws
