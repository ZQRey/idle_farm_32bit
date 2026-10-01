"""
Simulation Engine for Desktop Idle Farm.
Runs on a fixed tick rate independent of rendering FPS.
"""
import logging
import time
from typing import List, Optional, Callable

from src.core.constants import SIMULATION_TICK_INTERVAL, SIMULATION_TICKS_PER_SECOND

logger = logging.getLogger("simulation")


class SimulationEngine:
    """
    Fixed-rate simulation engine.
    Ticks at SIMULATION_TICKS_PER_SECOND independent of render FPS.
    """

    def __init__(self, tick_rate: int = SIMULATION_TICKS_PER_SECOND):
        self.tick_rate = tick_rate
        self.tick_interval = 1.0 / tick_rate
        self.tick_count = 0
        self.elapsed_time = 0.0
        self.speed_multiplier = 1
        self.paused = False
        self._accumulator = 0.0
        self._last_time = time.time()
        self._tick_callbacks: List[Callable[[float], None]] = []
        self._slow_tick_callbacks: List[Callable[[float], None]] = []  # Every 1 second
        self._slow_tick_counter = 0

    def register_tick(self, callback: Callable[[float], None]):
        """Register a callback for every simulation tick."""
        self._tick_callbacks.append(callback)

    def register_slow_tick(self, callback: Callable[[float], None]):
        """Register a callback for slow ticks (~1 per second)."""
        self._slow_tick_callbacks.append(callback)

    def update(self, dt: float):
        """
        Called from the main loop with delta time.
        Processes accumulated ticks at fixed rate.
        """
        if self.paused:
            self._last_time = time.time()
            return

        self._accumulator += dt * self.speed_multiplier

        # Prevent spiral of death - cap accumulator
        max_ticks = self.tick_rate * 2
        ticks_this_frame = 0

        while self._accumulator >= self.tick_interval and ticks_this_frame < max_ticks:
            self._do_tick()
            self._accumulator -= self.tick_interval
            ticks_this_frame += 1

        if ticks_this_frame >= max_ticks:
            self._accumulator = 0.0  # Drop excess time

    def _do_tick(self):
        """Execute one simulation tick."""
        self.tick_count += 1
        self.elapsed_time += self.tick_interval

        dt = self.tick_interval

        for callback in self._tick_callbacks:
            try:
                callback(dt)
            except Exception as e:
                logger.error(f"Tick callback error: {e}", exc_info=True)

        # Slow tick (approximately every second)
        self._slow_tick_counter += 1
        if self._slow_tick_counter >= self.tick_rate:
            self._slow_tick_counter = 0
            for callback in self._slow_tick_callbacks:
                try:
                    callback(1.0)
                except Exception as e:
                    logger.error(f"Slow tick callback error: {e}", exc_info=True)

    def simulate_offline(self, seconds: float, max_seconds: float = 43200):
        """
        Simulate offline progress.
        Uses simplified calculations for efficiency.
        """
        seconds = min(seconds, max_seconds)
        if seconds <= 0:
            return

        logger.info(f"Simulating offline progress: {seconds:.0f} seconds")

        # For offline, we use larger time steps for efficiency
        step_size = 10.0  # 10 second steps
        total_steps = int(seconds / step_size)

        for i in range(total_steps):
            for callback in self._tick_callbacks:
                try:
                    callback(step_size)
                except Exception as e:
                    logger.error(f"Offline tick error: {e}", exc_info=True)

        remainder = seconds - (total_steps * step_size)
        if remainder > 0:
            for callback in self._tick_callbacks:
                try:
                    callback(remainder)
                except Exception as e:
                    logger.error(f"Offline tick remainder error: {e}", exc_info=True)

        logger.info(f"Offline simulation complete: {total_steps} steps")

    def set_speed(self, multiplier: int):
        """Set simulation speed multiplier."""
        self.speed_multiplier = max(1, min(multiplier, 10))
        logger.info(f"Simulation speed: x{self.speed_multiplier}")

    def pause(self):
        """Pause simulation."""
        self.paused = True
        logger.info("Simulation paused")

    def resume(self):
        """Resume simulation."""
        self.paused = False
        self._last_time = time.time()
        self._accumulator = 0.0
        logger.info("Simulation resumed")
