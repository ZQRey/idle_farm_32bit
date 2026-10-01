"""
Game World - The main scene that manages all game entities and rendering.
Represents the farm strip visible above the Windows taskbar.
"""
import logging
import random
import math
import os
from typing import List, Optional, Dict

import pygame

from src.core.constants import TILE_SIZE, Colors, ASSETS_DIR, DAY_CYCLE_SECONDS
from src.rendering.renderer import Renderer, AssetManager, DayNightCycle
from src.fields.field import Field, TileState
from src.entities.vehicles.vehicle import (
    Vehicle, VehicleType, VehicleState, AttachmentType
)
from src.entities.workers.worker import (
    Worker, WorkerState, TaskType, Profession
)
from src.entities.animals.animals import FarmDog, FarmCat
from src.weather.weather_system import WeatherSystem, WeatherType
from src.economy.economy import Economy
from src.events.event_system import EventSystem
from src.ai.farm_ai import FarmAI
from src.crops.crop_data import CROP_DATA, calculate_yield, get_quality_price_modifier

logger = logging.getLogger("world")


class GameWorld:
    """
    The main game world managing all entities, simulation, and rendering.
    Laid out as a horizontal strip suitable for the desktop bar.
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

        # Core systems
        self.renderer = Renderer(width, height)
        self.weather = WeatherSystem()
        self.economy = Economy()
        self.events = EventSystem()
        self.farm_ai = FarmAI()

        # Entities
        self.fields: List[Field] = []
        self.vehicles: List[Vehicle] = []
        self.workers: List[Worker] = []
        self.dog: Optional[FarmDog] = None
        self.cat: Optional[FarmCat] = None

        # World layout constants (positions in the strip)
        # The strip is ~180px tall. Layout from top to bottom:
        # [sky ~34px] [hills/distant ~10px] [farm ground & fields ~70px] [road ~24px] [verge ~16px]
        self.sky_height = 34
        self.building_y = 36
        self.field_y = 74
        self.ground_y = self.height - 38  # Road begins here (~142)
        self.road_y = self.ground_y
        self.vehicle_y = self.ground_y - 24

        # Visual tile size
        self.tile_w = 10
        self.tile_h = 8

        # Buildings positions (world X coordinates)
        self.farmhouse_x = 45
        self.doghouse_x = 112
        self.barn_x = 150
        self.storage_x = 270
        self.silo_x = 340
        self.well_x = 395
        self.windmill_x = 1580
        self.pond_x = 1820

        # Field start position
        self.field_start_x = 450

        # Scroll
        self.camera_x = 0.0
        self.world_width = width

        # Farm level
        self.farm_level = 1
        self.farm_xp = 0
        self.farm_xp_to_next = 500

        # Playtime
        self.playtime = 0.0

        # Stats
        self.total_harvests = 0
        self.total_crops_sold = 0.0

        # Animated & rural entities
        self.chickens: List[Dict] = []
        self.cows: List[Dict] = []
        self.sheep: List[Dict] = []
        self.windmill_angle: float = 0.0
        self.windmill_frame: int = 0
        self.water_timer: float = 0.0
        self.floating_texts: List[Dict] = []
        self.hud_visible: bool = True
        self._last_money: float = 0.0

        # Particle pools
        self.dust_particles: List[Dict] = []
        self.grain_particles: List[Dict] = []

        # Work coordination
        self._work_timers: Dict[int, float] = {}  # worker_id -> timer

        # Fonts for HUD & floating texts
        self._font = None
        self._font_small = None

    def setup_new_game(self):
        """Initialize a new game with starting entities."""
        logger.info("Setting up new game with multi-field layout...")

        # Create starting fields across the screen width
        self.fields = [
            Field(1, 450, self.field_y, width=22, height=5, crop_type="wheat"),
            Field(2, 720, self.field_y, width=22, height=5, crop_type="corn"),
            Field(3, 990, self.field_y, width=22, height=5, crop_type="sunflower"),
            Field(4, 1260, self.field_y, width=20, height=5, crop_type="barley"),
        ]

        # Create starting vehicles
        tractor = Vehicle(VehicleType.SMALL_TRACTOR, self.barn_x + 65, self.vehicle_y)
        tractor.state = VehicleState.PARKED
        self.vehicles.append(tractor)

        tractor2 = Vehicle(VehicleType.MEDIUM_TRACTOR, self.barn_x + 115, self.vehicle_y)
        tractor2.state = VehicleState.PARKED
        self.vehicles.append(tractor2)

        combine = Vehicle(VehicleType.SMALL_COMBINE, self.barn_x + 175, self.vehicle_y - 6)
        combine.state = VehicleState.PARKED
        self.vehicles.append(combine)

        truck = Vehicle(VehicleType.FARM_TRUCK, self.storage_x + 45, self.vehicle_y)
        truck.state = VehicleState.PARKED
        self.vehicles.append(truck)

        # Create starting workers
        w1 = Worker(Profession.TRACTOR_DRIVER)
        w1.name = "Petr"
        w1.x = self.farmhouse_x + 30
        w1.y = self.ground_y
        self.workers.append(w1)

        w2 = Worker(Profession.FARM_WORKER)
        w2.name = "Ivan"
        w2.x = self.farmhouse_x + 50
        w2.y = self.ground_y
        self.workers.append(w2)

        w3 = Worker(Profession.AGRONOMIST)
        w3.name = "Anna"
        w3.x = self.farmhouse_x + 70
        w3.y = self.ground_y
        self.workers.append(w3)

        w4 = Worker(Profession.COMBINE_OPERATOR)
        w4.name = "Alexey"
        w4.x = self.barn_x + 25
        w4.y = self.ground_y
        self.workers.append(w4)

        # Create domestic animals
        self.dog = FarmDog(self.doghouse_x + 18, self.ground_y + 2)
        self.cat = FarmCat(self.barn_x + 12, self.building_y + 8)

        # Chickens in farmyard
        self.chickens = [
            {'x': 95.0, 'y': self.ground_y - 2, 'dir': 1, 'state': 0, 'timer': 1.2},
            {'x': 130.0, 'y': self.ground_y - 6, 'dir': -1, 'state': 1, 'timer': 2.0},
            {'x': 210.0, 'y': self.ground_y - 3, 'dir': 1, 'state': 0, 'timer': 0.8},
            {'x': 235.0, 'y': self.ground_y - 7, 'dir': -1, 'state': 1, 'timer': 1.5},
        ]

        # Cows in pasture paddock
        self.cows = [
            {'x': 1530.0, 'y': self.field_y + 8, 'frame': 0, 'timer': 3.2},
            {'x': 1600.0, 'y': self.field_y + 16, 'frame': 1, 'timer': 4.5},
        ]

        # Sheep in pasture paddock
        self.sheep = [
            {'x': 1660.0, 'y': self.field_y + 6, 'frame': 0, 'timer': 2.4},
            {'x': 1700.0, 'y': self.field_y + 18, 'frame': 1, 'timer': 3.7},
            {'x': 1740.0, 'y': self.field_y + 10, 'frame': 0, 'timer': 4.1},
        ]

        self._last_money = self.economy.money
        self._update_world_width()

        logger.info(f"New game created: {len(self.fields)} fields, "
                    f"{len(self.vehicles)} vehicles, {len(self.workers)} workers")

    def _update_world_width(self):
        """Calculate total world width based on content."""
        max_x = self.width
        for f in self.fields:
            end_x = f.x + f.width * self.tile_w
            max_x = max(max_x, end_x + 120)
        for v in self.vehicles:
            max_x = max(max_x, v.x + 100)
        self.world_width = max(self.width, max_x)

    def update(self, dt: float):
        """Update all game systems."""
        self.playtime += dt

        # Weather
        self.weather.update(dt, self.width)

        # Day/Night
        self.renderer.day_night.update(dt)

        # Fields - growth and weather effects
        weather_growth_mod = self.weather.growth_modifier
        for field in self.fields:
            field.update_growth(dt, weather_growth_mod)

            # Weather effects
            if self.weather.is_raining:
                field.apply_rain(dt, self.weather.intensity)
            if self.weather.current == WeatherType.HEAT:
                field.apply_heat(dt, self.weather.intensity)
            if self.weather.current == WeatherType.HAIL:
                if random.random() < 0.001 * dt:
                    field.apply_hail_damage(0.2)

        # Vehicles
        for vehicle in self.vehicles:
            vehicle.update(dt)

        # Workers
        for worker in self.workers:
            worker.update(dt)
            self._process_worker_task(worker, dt)

        # Domestic Animals
        is_raining = self.weather.is_raining
        is_night = self.renderer.day_night.is_night
        if self.dog:
            self.dog.update(dt, is_raining, is_night)
        if self.cat:
            self.cat.update(dt, is_raining, is_night)

        # Economy
        self.economy.update(dt)

        # Events
        self.events.update(dt, is_raining, is_night)

        # Farm AI - assign tasks
        self.farm_ai.update(dt, self.workers, self.vehicles, self.fields, self.economy)

        # Update animations & rural life
        self._update_animations(dt)

        # Update particles
        self._update_particles(dt)

    def _update_animations(self, dt: float):
        """Update ambient animations: windmill, livestock, floating texts."""
        # Windmill rotation based on wind speed
        wind_speed = 1.0 + self.weather.wind_speed * 1.5
        self.windmill_angle = (self.windmill_angle + dt * 4.0 * wind_speed) % 4.0
        self.windmill_frame = int(self.windmill_angle)

        # Water animation timer
        self.water_timer += dt

        # Chickens AI (pecking, clucking, hopping)
        for ch in self.chickens:
            ch['timer'] -= dt
            if ch['timer'] <= 0:
                ch['state'] = 1 - ch['state']  # Toggle between idle and pecking
                ch['timer'] = random.uniform(1.0, 3.0)
                if ch['state'] == 0 and random.random() < 0.4:
                    ch['dir'] = -ch['dir']
                    ch['x'] = max(70.0, min(260.0, ch['x'] + ch['dir'] * random.uniform(4, 12)))

        # Cows grazing toggle
        for cow in self.cows:
            cow['timer'] -= dt
            if cow['timer'] <= 0:
                cow['frame'] = 1 - cow['frame']
                cow['timer'] = random.uniform(2.5, 5.0)

        # Sheep grazing toggle
        for sh in self.sheep:
            sh['timer'] -= dt
            if sh['timer'] <= 0:
                sh['frame'] = 1 - sh['frame']
                sh['timer'] = random.uniform(2.0, 4.5)

        # Update floating texts
        alive_texts = []
        for ft in self.floating_texts:
            ft['life'] -= dt
            ft['y'] -= 14 * dt
            if ft['life'] > 0:
                alive_texts.append(ft)
        self.floating_texts = alive_texts

        # Farm XP progression check
        if self.farm_xp >= self.farm_xp_to_next:
            self.farm_level += 1
            self.farm_xp -= self.farm_xp_to_next
            self.farm_xp_to_next = int(self.farm_xp_to_next * 1.4)
            self.add_floating_text(f"LEVEL UP! Farm Lv.{self.farm_level}", 90, 42, (255, 230, 80))
            logger.info(f"Farm leveled up to Level {self.farm_level}!")

        # Economy money gain notification
        money_diff = self.economy.money - self._last_money
        if money_diff > 1.0:
            self.add_floating_text(f"+${money_diff:.0f}", self.storage_x + 40, self.vehicle_y - 12, (255, 220, 70))
        self._last_money = self.economy.money

    def add_floating_text(self, text: str, x: float, y: float, color=(255, 230, 80)):
        """Spawn floating feedback text in world."""
        self.floating_texts.append({
            'text': text,
            'x': float(x),
            'y': float(y),
            'color': color,
            'life': 2.0,
            'max_life': 2.0
        })

    def _process_worker_task(self, worker: Worker, dt: float):
        """Process the worker's current task - coordinate with vehicles and fields."""
        if worker.current_task == TaskType.NONE:
            return

        # Track work timers
        if worker.id not in self._work_timers:
            self._work_timers[worker.id] = 0
        self._work_timers[worker.id] += dt

        # If walking to destination, wait
        if worker.moving:
            return

        vehicle = None
        if worker.assigned_vehicle_id:
            vehicle = next((v for v in self.vehicles if v.id == worker.assigned_vehicle_id), None)

        field = None
        if worker.assigned_field_id:
            field = next((f for f in self.fields if f.field_id == worker.assigned_field_id), None)

        # Handle arriving at vehicle
        if vehicle and worker.state == WorkerState.IDLE and worker.current_task != TaskType.NONE:
            if abs(worker.x - vehicle.x) < 30:
                # Worker is near vehicle - start driving
                worker.state = WorkerState.DRIVING
                worker.x = vehicle.x  # Snap to vehicle
                worker.moving = False

                # Start vehicle work
                if field and worker.current_task in (
                    TaskType.PLOW_FIELD, TaskType.SEED_FIELD,
                    TaskType.CULTIVATE_FIELD, TaskType.HARVEST_FIELD
                ):
                    vehicle.move_to(field.x)
                    vehicle.start_work(field.field_id)

        # Process active work
        if worker.state == WorkerState.DRIVING and vehicle:
            # Worker rides with vehicle
            worker.x = vehicle.x + 10
            worker.direction = vehicle.direction

            # Check if vehicle arrived at field
            if field and not vehicle.moving and vehicle.state == VehicleState.WORKING:
                self._do_field_work(worker, vehicle, field, dt)

        # Inspect task (no vehicle needed)
        elif worker.current_task == TaskType.INSPECT_CROP and field:
            if not worker.moving:
                worker.state = WorkerState.INSPECTING
                worker.work_timer += dt
                if worker.work_timer >= 5:  # 5 seconds to inspect
                    worker.work_timer = 0
                    # Inspection improves crop quality
                    for row in field.tiles:
                        for tile in row:
                            tile.health = min(1.0, tile.health + 0.01)
                    worker.gain_xp(5)
                    worker.current_task = TaskType.NONE
                    worker.state = WorkerState.IDLE
                    worker.assigned_field_id = None

        # Repair task
        elif worker.current_task == TaskType.REPAIR_VEHICLE:
            target_v = next((v for v in self.vehicles
                            if v.id == worker.assigned_vehicle_id), None)
            if target_v and not worker.moving:
                if abs(worker.x - target_v.x) < 20:
                    worker.state = WorkerState.REPAIRING
                    worker.work_timer += dt
                    if worker.work_timer >= 10:  # 10 seconds to repair
                        target_v.repair(30 + worker.repair * 0.5)
                        worker.gain_xp(10)
                        worker.work_timer = 0
                        worker.current_task = TaskType.NONE
                        worker.state = WorkerState.IDLE
                        worker.assigned_vehicle_id = None
                        self.economy.spend(target_v.data.get('repair_cost', 200) * 0.3,
                                          f"Repair {target_v.data['name']}")
                else:
                    worker.move_to(target_v.x)

    def _do_field_work(self, worker: Worker, vehicle: Vehicle, field: Field, dt: float):
        """Process field work - plowing, seeding, harvesting tile by tile."""
        task = worker.current_task
        work_speed = vehicle.work_speed * worker.work_modifier * self.weather.work_speed_modifier

        if task == TaskType.PLOW_FIELD:
            target_state = TileState.UNTOUCHED
            new_state = TileState.PLOWED
            next_task_state = None
        elif task == TaskType.CULTIVATE_FIELD:
            target_state = TileState.PLOWED
            new_state = TileState.CULTIVATED
            next_task_state = None
        elif task == TaskType.SEED_FIELD:
            target_state = TileState.CULTIVATED
            new_state = TileState.SEEDED
            next_task_state = None
        elif task == TaskType.HARVEST_FIELD:
            target_state = TileState.READY
            new_state = TileState.HARVESTED
            next_task_state = None
        else:
            return

        # Find next tile to work on
        tile = field.get_next_work_tile(target_state)
        if tile is None:
            # Check if we should also process HARVESTED tiles as UNTOUCHED for plowing
            if task == TaskType.PLOW_FIELD:
                tile = field.get_next_work_tile(TileState.HARVESTED)

        if tile is None:
            # Work complete!
            logger.info(f"Field work complete: {task.name} on field {field.field_id}")
            worker.gain_xp(20)

            if task == TaskType.SEED_FIELD:
                # Set crop type on all seeded tiles
                for row in field.tiles:
                    for t in row:
                        if t.state == TileState.SEEDED:
                            t.crop_type = field.crop_type

            if task == TaskType.HARVEST_FIELD:
                # Calculate and store harvest
                crop_data = CROP_DATA.get(field.crop_type, CROP_DATA['wheat'])
                avg_quality = 50
                quality_count = 0
                for row in field.tiles:
                    for t in row:
                        if t.quality > 0:
                            avg_quality += t.quality
                            quality_count += 1
                if quality_count > 0:
                    avg_quality /= quality_count

                total_yield = calculate_yield(
                    crop_data['base_yield'],
                    0.7,  # avg fertility
                    0.5,  # avg moisture
                    self.weather.growth_modifier,
                    worker.work_modifier,
                    vehicle.work_speed,
                    0.0  # damage
                )

                stored = self.economy.storage.add(field.crop_type, total_yield)
                self.economy.total_harvested += stored
                self.total_harvests += 1
                self.farm_xp += int(total_yield / 10)

                logger.info(f"Harvested {stored:.0f}kg {field.crop_type} "
                           f"(quality: {avg_quality:.0f})")

                field.reset_after_harvest()

            # Release vehicle and worker
            self._finish_work(worker, vehicle)
            return

        # Move vehicle toward tile
        tile_world_x = field.x + tile.x * self.tile_w
        if abs(vehicle.x - tile_world_x) > 4:
            vehicle.target_x = tile_world_x
            vehicle.direction = 1 if tile_world_x > vehicle.x else -1
        else:
            # Work on tile
            worker.work_timer += dt * work_speed
            if worker.work_timer >= 0.5:  # 0.5 seconds per tile
                worker.work_timer = 0
                old_state = tile.state
                tile.state = new_state

                if new_state == TileState.SEEDED:
                    tile.crop_type = field.crop_type
                    tile.growth_progress = 0.0

                # Fuel consumption
                vehicle.fuel -= vehicle.fuel_consumption * 2

                # Spawn dust
                self.dust_particles.append({
                    'x': tile_world_x,
                    'y': self.field_y + tile.y * self.tile_h,
                    'life': 0.8,
                    'vx': random.uniform(-10, 10),
                    'vy': random.uniform(-15, -5),
                })

    def _finish_work(self, worker: Worker, vehicle: Vehicle):
        """Finish a work task and release entities."""
        worker.current_task = TaskType.NONE
        worker.state = WorkerState.IDLE
        worker.assigned_vehicle_id = None
        worker.assigned_field_id = None
        worker.work_timer = 0

        vehicle.state = VehicleState.PARKED
        vehicle.driver_id = None
        vehicle.moving = False
        vehicle.target_x = None

        # Worker exits vehicle
        worker.x = vehicle.x + 20
        worker.moving = False

    def _update_particles(self, dt: float):
        """Update all particle effects."""
        alive = []
        for p in self.dust_particles:
            p['life'] -= dt * 1.5
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] += 15 * dt  # gravity
            if p['life'] > 0:
                alive.append(p)
        self.dust_particles = alive[:50]

    # ========== RENDERING PIPELINE ==========

    def draw(self, screen: pygame.Surface):
        """Draw the entire game world in layered pixel-art glory."""
        # 1. Clear with color key (magenta for desktop transparency)
        screen.fill((255, 0, 255))

        # 2. Sky gradient
        self.renderer.draw_sky(screen, self.sky_height)

        # 3. Clouds drifting in sky
        self._draw_clouds(screen)

        # 4. Distant rolling hills & mountain ridge
        self._draw_background(screen)

        # 5. Base countryside ground & terrain (covers meadow, farmyard, fields, pasture)
        self._draw_terrain_base(screen)

        # 6. Buildings & rural structures
        self._draw_buildings(screen)

        # 7. Environmental decorations (scarecrows, fences, hay, pond, flowers)
        self._draw_decorations(screen)

        # 8. Agricultural fields (plowed soil, seed, sprouts, golden crops)
        self._draw_fields(screen)

        # 9. Animals (dog, cat, chickens, cows, sheep)
        self._draw_animals(screen)

        # 10. Country road
        self._draw_road(screen)

        # 11. Farm vehicles & machinery with attachments
        self._draw_vehicles(screen)

        # 12. Workers & farmers
        self._draw_workers(screen)

        # 13. Foreground roadside verge with grass tufts and wildflowers
        self._draw_foreground(screen)

        # 14. Weather particles (rain/snow/hail)
        self._draw_weather(screen)

        # 15. World particles (dust, exhaust smoke, grain)
        self._draw_particles(screen)

        # 16. Day/night ambient tint overlay
        self.renderer.draw_day_night_overlay(screen)

        # 17. Night lights (windows, lamps, vehicle headlights)
        if self.renderer.day_night.show_lights:
            self._draw_lights(screen)

        # 18. Floating feedback text popups (+$150, +XP, Level Up)
        self._draw_floating_texts(screen)

        # 19. Miniature pixel-art HUD status bar
        if self.hud_visible:
            self._draw_hud(screen)

    def _draw_background(self, screen: pygame.Surface):
        """Draw distant rolling hills and treeline silhouette along the horizon."""
        hill_color_back = (75, 125, 68)
        hill_color_front = (88, 142, 78)

        # Distant hill wave
        for x in range(0, self.width + 60, 60):
            h = 10 + int(math.sin(x * 0.015) * 5)
            pygame.draw.polygon(screen, hill_color_back, [
                (x, self.sky_height),
                (x + 30, self.sky_height - h),
                (x + 60, self.sky_height),
            ])

        # Closer hill wave
        for x in range(0, self.width + 80, 80):
            h = 8 + int(math.cos(x * 0.02) * 6)
            pygame.draw.polygon(screen, hill_color_front, [
                (x, self.sky_height),
                (x + 40, self.sky_height - h),
                (x + 80, self.sky_height),
            ])

        # Treeline on distant hills
        tree_sprite = self.renderer.assets.get_sprite("environment/tree.png")
        if tree_sprite:
            scaled_tree = pygame.transform.scale(tree_sprite, (12, 18))
            for x in range(15, self.width, 50):
                # Small offset based on sine wave
                y_off = int(math.sin(x * 0.02) * 4)
                screen.blit(scaled_tree, (x, self.sky_height - 14 - y_off))

    def _draw_terrain_base(self, screen: pygame.Surface):
        """Draw cohesive countryside terrain filling from horizon to road."""
        # 1. Base meadow grass across entire ground strip
        base_grass = (76, 145, 65)
        pygame.draw.rect(screen, base_grass, (0, self.sky_height - 2, self.width, self.height - self.sky_height + 2))

        # Upper meadow gentle color variation
        for x in range(0, self.width, 32):
            pygame.draw.rect(screen, (84, 156, 73), (x, self.sky_height, 16, 20))
            pygame.draw.rect(screen, (70, 136, 60), (x + 16, self.sky_height + 4, 16, 16))

        # 2. Farmyard dirt & gravel zone on left (around farmhouse, barn, silo, storage, well)
        yard_rect = (0, self.building_y + 8, self.field_start_x - 18, self.ground_y - (self.building_y + 8))
        pygame.draw.rect(screen, (138, 98, 58), yard_rect, border_top_right_radius=8, border_bottom_right_radius=6)
        # Texture yard with dirt & gravel ruts
        for y in range(int(self.building_y + 12), int(self.ground_y), 6):
            for x in range(10, self.field_start_x - 30, 24):
                if (x + y) % 8 == 0:
                    pygame.draw.rect(screen, (122, 84, 48), (x, y, 6, 2))
                elif (x * 3 + y) % 11 == 0:
                    pygame.draw.rect(screen, (156, 114, 70), (x + 3, y + 1, 4, 2))

        # Boundary fence with gate separating farmyard from fields
        fence_sprite = self.renderer.assets.get_sprite('environment/fence.png')
        if fence_sprite:
            f_post = pygame.transform.scale(fence_sprite, (6, 12))
            for fy in range(int(self.building_y + 10), int(self.ground_y) - 24, 12):
                screen.blit(f_post, (self.field_start_x - 18, fy))

        # Cobblestone / packed dirt pathways connecting doors to the road
        # Path from farmhouse
        pygame.draw.polygon(screen, (165, 140, 100), [
            (self.farmhouse_x + 20, self.building_y + 36),
            (self.farmhouse_x + 36, self.building_y + 36),
            (self.farmhouse_x + 48, self.ground_y),
            (self.farmhouse_x + 28, self.ground_y),
        ])
        # Path from barn
        pygame.draw.polygon(screen, (165, 140, 100), [
            (self.barn_x + 18, self.building_y + 36),
            (self.barn_x + 36, self.building_y + 36),
            (self.barn_x + 42, self.ground_y),
            (self.barn_x + 22, self.ground_y),
        ])

        # 3. Farmland soil base under each field plot
        for f in self.fields:
            fx = f.x - 4
            fy = self.field_y - 3
            fw = f.width * self.tile_w + 8
            fh = f.height * self.tile_h + 6
            # Soil border
            pygame.draw.rect(screen, (75, 52, 32), (fx, fy, fw, fh), border_radius=3)
            # Rich dark soil bed
            pygame.draw.rect(screen, (96, 68, 42), (fx + 2, fy + 2, fw - 4, fh - 4), border_radius=2)
            # Furrow lines
            for r in range(f.height):
                ry = self.field_y + r * self.tile_h + self.tile_h - 1
                pygame.draw.line(screen, (80, 56, 34), (fx + 3, ry), (fx + fw - 4, ry))

        # 4. Animal Pasture paddock (fresh lush grass zone)
        pasture_x = 1500
        pasture_w = 300
        pasture_rect = (pasture_x, self.field_y - 8, pasture_w, self.ground_y - self.field_y + 8)
        pygame.draw.rect(screen, (82, 155, 72), pasture_rect, border_radius=4)
        for px in range(pasture_x + 10, pasture_x + pasture_w - 10, 20):
            pygame.draw.rect(screen, (92, 168, 80), (px, self.field_y, 8, 8))

    def _draw_buildings(self, screen: pygame.Surface):
        """Draw farm buildings and architectural structures."""
        assets = self.renderer.assets
        is_night = self.renderer.day_night.show_lights

        # Grounding shadows under buildings
        shadow_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for bx, by, bw in [
            (self.farmhouse_x, self.building_y + 44, 48),
            (self.doghouse_x, self.ground_y - 2, 16),
            (self.barn_x, self.building_y + 44, 52),
            (self.storage_x, self.building_y + 44, 38),
            (self.silo_x, self.building_y + 44, 20),
            (self.well_x, self.building_y + 42, 20),
            (self.windmill_x, self.building_y + 50, 32),
        ]:
            pygame.draw.ellipse(shadow_surf, (20, 20, 20, 60), (bx - 2, by - 2, bw + 4, 5))
        screen.blit(shadow_surf, (0, 0))

        # Farmhouse
        fh_key = 'buildings/farmhouse_night.png' if is_night else 'buildings/farmhouse.png'
        fh = assets.get_sprite(fh_key)
        if fh:
            scaled = pygame.transform.scale(fh, (48, 36))
            screen.blit(scaled, (self.farmhouse_x, self.building_y + 8))

        # Doghouse
        dh = assets.get_sprite('buildings/doghouse.png')
        if dh:
            scaled = pygame.transform.scale(dh, (16, 16))
            screen.blit(scaled, (self.doghouse_x, self.ground_y - 18))

        # Barn
        barn = assets.get_sprite('buildings/barn.png')
        if barn:
            scaled = pygame.transform.scale(barn, (52, 38))
            screen.blit(scaled, (self.barn_x, self.building_y + 6))

        # Storage / Warehouse
        storage = assets.get_sprite('buildings/storage.png')
        if storage:
            scaled = pygame.transform.scale(storage, (38, 26))
            screen.blit(scaled, (self.storage_x, self.building_y + 18))

        # Silo
        silo = assets.get_sprite('buildings/silo.png')
        if silo:
            scaled = pygame.transform.scale(silo, (20, 38))
            screen.blit(scaled, (self.silo_x, self.building_y + 6))

        # Water Well
        well = assets.get_sprite('buildings/well.png')
        if well:
            scaled = pygame.transform.scale(well, (20, 24))
            screen.blit(scaled, (self.well_x, self.building_y + 18))

        # Windmill
        wt = assets.get_sprite('buildings/windmill_tower.png')
        if wt:
            scaled_tower = pygame.transform.scale(wt, (32, 48))
            screen.blit(scaled_tower, (self.windmill_x, self.building_y + 2))

            # Rotating blades
            wb = assets.get_sprite(f'buildings/windmill_blades_{self.windmill_frame}.png')
            if wb:
                scaled_blades = pygame.transform.scale(wb, (34, 34))
                screen.blit(scaled_blades, (self.windmill_x - 1, self.building_y - 8))

    def _draw_decorations(self, screen: pygame.Surface):
        """Draw scarecrows, fences, hay bales, crates, pond, and flowers."""
        assets = self.renderer.assets

        # Scarecrows in fields
        scarecrow = assets.get_sprite('environment/scarecrow.png')
        if scarecrow:
            sc_scaled = pygame.transform.scale(scarecrow, (14, 20))
            screen.blit(sc_scaled, (700, self.field_y - 8))
            screen.blit(sc_scaled, (1235, self.field_y - 8))

        # Field Fences
        fence = assets.get_sprite('environment/fence_h.png')
        if not fence:
            fence = assets.get_sprite('environment/fence.png')
        if fence:
            f_scaled = pygame.transform.scale(fence, (20, 10))
            # Field 1 top fence
            for x in range(446, 680, 20):
                screen.blit(f_scaled, (x, self.field_y - 10))
            # Field 2 top fence
            for x in range(716, 950, 20):
                screen.blit(f_scaled, (x, self.field_y - 10))
            # Pasture Paddock perimeter fence
            for x in range(1500, 1800, 20):
                screen.blit(f_scaled, (x, self.field_y - 10))
                screen.blit(f_scaled, (x, self.ground_y - 12))

        # Pond
        pond = assets.get_sprite('environment/pond.png')
        if pond:
            p_scaled = pygame.transform.scale(pond, (48, 18))
            screen.blit(p_scaled, (self.pond_x, self.field_y + 10))
            # Water sparkle
            if int(self.water_timer * 3) % 2 == 0:
                pygame.draw.circle(screen, (240, 250, 255), (self.pond_x + 22, self.field_y + 18), 1)
                pygame.draw.circle(screen, (240, 250, 255), (self.pond_x + 34, self.field_y + 16), 1)

        # Hay bales near barn
        hay = assets.get_sprite('environment/hay.png')
        if hay:
            scaled = pygame.transform.scale(hay, (13, 9))
            screen.blit(scaled, (self.barn_x + 55, self.ground_y - 11))
            screen.blit(scaled, (self.barn_x + 69, self.ground_y - 11))
            screen.blit(scaled, (self.barn_x + 62, self.ground_y - 19))  # Top stacked bale

        # Crates near storage
        crate = assets.get_sprite('environment/crate.png')
        if crate:
            c_scaled = pygame.transform.scale(crate, (10, 10))
            screen.blit(c_scaled, (self.storage_x + 39, self.ground_y - 12))
            screen.blit(c_scaled, (self.storage_x + 50, self.ground_y - 12))

        # Flowers
        for color in ['red', 'yellow', 'white', 'purple']:
            flower = assets.get_sprite(f'environment/flower_{color}.png')
            if flower:
                f_scaled = pygame.transform.scale(flower, (6, 6))
                for ox in [30, 90, 205, 415, 690, 965, 1235, 1490]:
                    fx = ox + (hash(color) % 20)
                    screen.blit(f_scaled, (fx, self.ground_y - 7))

        # Lamp posts
        lamp = assets.get_sprite('environment/lamp.png')
        if lamp:
            scaled = pygame.transform.scale(lamp, (6, 18))
            for lx in [self.farmhouse_x - 10, self.barn_x - 10, self.storage_x - 10, 1485]:
                screen.blit(scaled, (lx, self.ground_y - 18))

    def _draw_fields(self, screen: pygame.Surface):
        """Draw agricultural fields with tile states and crop stages."""
        assets = self.renderer.assets

        state_sprites = {
            TileState.UNTOUCHED: 'terrain/grass.png',
            TileState.PLOWED: 'terrain/dirt_plowed.png',
            TileState.CULTIVATED: 'terrain/dirt_cultivated.png',
            TileState.SEEDED: 'terrain/dirt_seeded.png',
            TileState.GROWING1: 'terrain/dirt_seeded.png',
            TileState.GROWING2: 'terrain/dirt_seeded.png',
            TileState.GROWING3: 'terrain/dirt_seeded.png',
            TileState.MATURE: 'terrain/dirt_seeded.png',
            TileState.READY: 'terrain/dirt_seeded.png',
            TileState.HARVESTED: 'terrain/dirt.png',
        }

        crop_state_sprites = {
            TileState.SEEDED: 'seed',
            TileState.GROWING1: 'sprout',
            TileState.GROWING2: 'young',
            TileState.GROWING3: 'growing',
            TileState.MATURE: 'mature',
            TileState.READY: 'ready',
        }

        tile_w = self.tile_w
        tile_h = self.tile_h

        for field in self.fields:
            for row_idx, row in enumerate(field.tiles):
                for col_idx, tile in enumerate(row):
                    tx = field.x + col_idx * tile_w
                    ty = self.field_y + row_idx * tile_h

                    # Draw terrain tile
                    terrain_key = state_sprites.get(tile.state, 'terrain/dirt_plowed.png')
                    terrain_sprite = assets.get_sprite(terrain_key)
                    if terrain_sprite:
                        scaled = pygame.transform.scale(terrain_sprite, (tile_w, tile_h))
                        screen.blit(scaled, (tx, ty))
                    else:
                        color = (100, 70, 42) if tile.state != TileState.UNTOUCHED else Colors.GRASS
                        pygame.draw.rect(screen, color, (tx, ty, tile_w, tile_h))

                    # Draw crop overlay with subtle wind sway
                    if tile.crop_type and tile.state in crop_state_sprites:
                        crop_stage = crop_state_sprites[tile.state]
                        crop_folder = CROP_DATA.get(tile.crop_type, {}).get(
                            'sprite_folder', 'crops/wheat')
                        crop_key = f"{crop_folder}/{crop_stage}.png"
                        crop_sprite = assets.get_sprite(crop_key)
                        if crop_sprite:
                            crop_h = min(tile_h + 4, crop_sprite.get_height())
                            scaled = pygame.transform.scale(crop_sprite, (tile_w, crop_h))
                            # Subtle sway for tall crops
                            sway = int(math.sin(self.playtime * 2.5 + tx * 0.1) * 1) if crop_stage in ('mature', 'ready') else 0
                            screen.blit(scaled, (tx + sway, ty - crop_h + tile_h))

    def _draw_animals(self, screen: pygame.Surface):
        """Draw domestic animals and pasture livestock."""
        assets = self.renderer.assets

        # Dog
        if self.dog:
            sprite = assets.get_sprite(self.dog.sprite_key)
            y = self.ground_y - 2
            if self.dog.state.name == 'SLEEPING':
                y = self.ground_y
            if sprite:
                scaled = pygame.transform.scale(sprite, (12, 12))
                screen.blit(scaled, (int(self.dog.x), int(y)))

        # Cat
        if self.cat:
            sprite = assets.get_sprite(self.cat.sprite_key)
            y = self.ground_y - 2
            if self.cat.on_roof:
                y = self.building_y + 8
            if sprite:
                scaled = pygame.transform.scale(sprite, (9, 9))
                screen.blit(scaled, (int(self.cat.x), int(y)))

        # Chickens in yard
        for ch in self.chickens:
            ch_sprite = assets.get_sprite(f"animals/chicken_{ch['state']}.png")
            if ch_sprite:
                scaled = pygame.transform.scale(ch_sprite, (8, 8))
                if ch['dir'] < 0:
                    scaled = pygame.transform.flip(scaled, True, False)
                screen.blit(scaled, (int(ch['x']), int(ch['y'])))

        # Cows in pasture
        for cow in self.cows:
            cow_sprite = assets.get_sprite(f"animals/cow_{cow['frame']}.png")
            if cow_sprite:
                scaled = pygame.transform.scale(cow_sprite, (22, 15))
                screen.blit(scaled, (int(cow['x']), int(cow['y'])))

        # Sheep in pasture
        for sh in self.sheep:
            sh_sprite = assets.get_sprite(f"animals/sheep_{sh['frame']}.png")
            if sh_sprite:
                scaled = pygame.transform.scale(sh_sprite, (16, 12))
                screen.blit(scaled, (int(sh['x']), int(sh['y'])))

    def _draw_road(self, screen: pygame.Surface):
        """Draw country road with tire ruts along the lower zone."""
        road_y = self.ground_y
        road_h = 24

        # Packed dirt road base
        pygame.draw.rect(screen, (170, 142, 102), (0, road_y, self.width, road_h))

        # Upper and lower tire grooves
        pygame.draw.rect(screen, (148, 120, 84), (0, road_y + 5, self.width, 3))
        pygame.draw.rect(screen, (148, 120, 84), (0, road_y + 14, self.width, 3))

        # Gravel and stone details along road
        for x in range(0, self.width, 28):
            pygame.draw.rect(screen, (135, 110, 75), (x + 8, road_y + 6, 4, 1))
            pygame.draw.rect(screen, (135, 110, 75), (x + 18, road_y + 15, 3, 1))

    def _draw_vehicles(self, screen: pygame.Surface):
        """Draw tractors, combines, trucks with working implement attachments."""
        assets = self.renderer.assets

        for vehicle in self.vehicles:
            # 1. Draw vehicle body
            sprite = assets.get_sprite(vehicle.sprite_key)
            sw = int(vehicle.data['size'][0] * 0.65)
            sh = int(vehicle.data['size'][1] * 0.65)

            if sprite:
                scaled = pygame.transform.scale(sprite, (sw, sh))
                screen.blit(scaled, (int(vehicle.x), int(vehicle.y)))
            else:
                color = (60, 130, 50) if 'tractor' in vehicle.vehicle_type.name.lower() else (100, 100, 110)
                pygame.draw.rect(screen, color, (int(vehicle.x), int(vehicle.y), sw, sh))

            # 2. Draw working attachment behind vehicle
            if vehicle.attachment != AttachmentType.NONE:
                att_key = None
                if vehicle.attachment == AttachmentType.PLOW:
                    att_key = 'environment/plow.png'
                elif vehicle.attachment == AttachmentType.SEEDER:
                    att_key = 'environment/seeder.png'
                elif vehicle.attachment == AttachmentType.TRAILER:
                    att_key = 'environment/trailer.png'
                elif vehicle.attachment == AttachmentType.CULTIVATOR:
                    att_key = 'environment/plow.png'

                if att_key:
                    att_sprite = assets.get_sprite(att_key)
                    if att_sprite:
                        aw = int(att_sprite.get_width() * 0.6)
                        ah = int(att_sprite.get_height() * 0.6)
                        scaled_att = pygame.transform.scale(att_sprite, (aw, ah))
                        # Attach to rear
                        att_x = vehicle.x - aw + 2 if vehicle.direction > 0 else vehicle.x + sw - 2
                        screen.blit(scaled_att, (int(att_x), int(vehicle.y + 4)))

            # 3. Draw dust from tires
            for p in vehicle.dust_particles:
                alpha = int(p['life'] * 150)
                if alpha > 0:
                    pygame.draw.circle(screen, (160, 140, 100), (int(p['x']), int(p['y'])), 2)

    def _draw_workers(self, screen: pygame.Surface):
        """Draw farmers and workers."""
        assets = self.renderer.assets

        for worker in self.workers:
            if worker.state == WorkerState.DRIVING:
                continue  # Inside vehicle cabin

            sprite = assets.get_sprite(worker.sprite_key)
            if sprite:
                scaled = pygame.transform.scale(sprite, (11, 22))
                screen.blit(scaled, (int(worker.x), int(self.ground_y - 21)))
            else:
                pygame.draw.rect(screen, Colors.SHIRT_BLUE, (int(worker.x), int(self.ground_y - 18), 6, 18))
                pygame.draw.rect(screen, Colors.SKIN, (int(worker.x) + 1, int(self.ground_y - 22), 4, 4))

    def _draw_foreground(self, screen: pygame.Surface):
        """Draw roadside verge with grass tufts and wildflowers along the bottom."""
        fg_y = self.ground_y + 24
        fg_h = self.height - fg_y

        # Deep green grass border
        pygame.draw.rect(screen, (58, 120, 50), (0, fg_y, self.width, fg_h))

        # Grass blades
        for x in range(0, self.width, 10):
            h = random.Random(x + 50).randint(4, 8)
            pygame.draw.line(screen, (68, 138, 58), (x, fg_y), (x - 1, fg_y - h + 2))
            pygame.draw.line(screen, (78, 150, 68), (x + 2, fg_y), (x + 2, fg_y - h + 1))

        # Wildflowers along bottom edge
        for x in range(8, self.width, 36):
            c_idx = (x // 36) % 3
            f_color = [(225, 70, 60), (245, 215, 60), (245, 245, 240)][c_idx]
            pygame.draw.circle(screen, f_color, (x, fg_y + 3), 2)
            pygame.draw.circle(screen, (255, 230, 100), (x, fg_y + 3), 1)

    def _draw_clouds(self, screen: pygame.Surface):
        """Draw weather clouds."""
        assets = self.renderer.assets

        for cloud_data in self.weather.cloud_positions:
            key = 'weather/cloud.png' if cloud_data['type'] == 'light' else 'weather/cloud_dark.png'
            cloud = assets.get_sprite(key)
            if cloud:
                scaled = pygame.transform.scale(cloud, (36, 15))
                screen.blit(scaled, (int(cloud_data['x']), int(cloud_data['y'])))

    def _draw_weather(self, screen: pygame.Surface):
        """Draw rain, snow, hail particles."""
        if self.weather.is_raining:
            rain_color = Colors.RAIN_DROP
            for p in self.weather.rain_particles:
                x, y = int(p['x']), int(p['y'])
                if 0 <= x < self.width and 0 <= y < self.height:
                    length = min(p['length'], 6)
                    pygame.draw.line(screen, rain_color, (x, y), (x - 1, y + length), 1)

        if self.weather.current == WeatherType.SNOW:
            for p in self.weather.snow_particles:
                x, y = int(p['x']), int(p['y'])
                if 0 <= x < self.width and 0 <= y < self.height:
                    pygame.draw.circle(screen, Colors.SNOW_FLAKE, (x, y), 1)

        if self.weather.current == WeatherType.HAIL:
            for p in self.weather.rain_particles:
                x, y = int(p['x']), int(p['y'])
                if 0 <= x < self.width and 0 <= y < self.height:
                    pygame.draw.circle(screen, (200, 210, 225), (x, y), 2)

    def _draw_particles(self, screen: pygame.Surface):
        """Draw dust and harvest particles."""
        for p in self.dust_particles:
            x, y = int(p['x']), int(p['y'])
            alpha = p['life']
            if 0 <= x < self.width and 0 <= y < self.height:
                size = max(1, int(alpha * 3))
                pygame.draw.circle(screen, (160, 140, 100), (x, y), size)

    def _draw_lights(self, screen: pygame.Surface):
        """Draw cozy night lights (windows, lantern glow, headlights)."""
        # Lantern glows
        for x in [self.farmhouse_x - 7, self.barn_x - 7, self.storage_x - 7, 1488]:
            glow_surf = pygame.Surface((18, 18), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 220, 120, 70), (9, 9), 9)
            pygame.draw.circle(glow_surf, (255, 240, 180, 120), (9, 9), 4)
            screen.blit(glow_surf, (x - 6, self.ground_y - 25))

        # Vehicle headlights
        for vehicle in self.vehicles:
            if vehicle.state in (VehicleState.DRIVING, VehicleState.WORKING):
                hx = vehicle.x + (vehicle.data['size'][0] * 0.65 if vehicle.direction > 0 else 0)
                hy = vehicle.y + 7
                glow_surf = pygame.Surface((30, 16), pygame.SRCALPHA)
                pygame.draw.ellipse(glow_surf, (255, 240, 180, 60), (0, 0, 30, 16))
                screen.blit(glow_surf, (int(hx) - (5 if vehicle.direction > 0 else 25), int(hy) - 8))

    def _draw_floating_texts(self, screen: pygame.Surface):
        """Draw floating gain feedback (+$XX, +XP, Level up)."""
        if not self._font:
            try:
                self._font = pygame.font.SysFont('consolas', 12, bold=True)
            except Exception:
                self._font = pygame.font.Font(None, 16)

        for ft in self.floating_texts:
            alpha = max(0.0, min(1.0, ft['life'] / ft['max_life']))
            text_surf = self._font.render(ft['text'], True, ft['color'])
            # Shadow
            shadow_surf = self._font.render(ft['text'], True, (20, 20, 20))
            screen.blit(shadow_surf, (int(ft['x']) + 1, int(ft['y']) + 1))
            screen.blit(text_surf, (int(ft['x']), int(ft['y'])))

    def _draw_hud(self, screen: pygame.Surface):
        """Draw miniature pixel-art status bar on top."""
        if not self._font_small:
            try:
                self._font_small = pygame.font.SysFont('consolas', 11, bold=True)
            except Exception:
                self._font_small = pygame.font.Font(None, 14)

        # Weather icon lookup
        weather_icons = {
            WeatherType.CLEAR: "SUN",
            WeatherType.CLOUDY: "CLD",
            WeatherType.RAIN: "RAIN",
            WeatherType.HEAVY_RAIN: "H-RAIN",
            WeatherType.STORM: "STRM",
            WeatherType.HEAT: "HEAT",
            WeatherType.STRONG_WIND: "WIND",
            WeatherType.SNOW: "SNOW",
            WeatherType.HAIL: "HAIL",
            WeatherType.FOG: "FOG",
        }
        w_icon = weather_icons.get(self.weather.current, "SUN")
        phase = self.renderer.day_night.phase.upper()

        hud_text = (
            f" [LV.{self.farm_level}] "
            f" ${self.economy.money:,.0f} | "
            f" FUEL:{self.economy.fuel:.0f}L | "
            f" SILO:{self.economy.storage.total_stored:.0f}/{self.economy.storage.capacity:.0f}kg | "
            f" {w_icon} | {phase} "
        )

        ts = self._font_small.render(hud_text, True, (240, 240, 245))
        tw, th = ts.get_size()

        # HUD backing pill
        hud_bg = pygame.Surface((tw + 12, th + 4), pygame.SRCALPHA)
        pygame.draw.rect(hud_bg, (22, 26, 34, 190), (0, 0, tw + 12, th + 4), border_radius=4)
        pygame.draw.rect(hud_bg, (60, 68, 80, 190), (0, 0, tw + 12, th + 4), width=1, border_radius=4)

        hx = self.width - tw - 24
        hy = 6
        screen.blit(hud_bg, (hx, hy))
        screen.blit(ts, (hx + 6, hy + 2))

    # ========== SERIALIZATION ==========

    def to_dict(self) -> dict:
        return {
            'playtime': self.playtime,
            'farm_level': self.farm_level,
            'farm_xp': self.farm_xp,
            'farm_xp_to_next': self.farm_xp_to_next,
            'total_harvests': self.total_harvests,
            'total_crops_sold': self.total_crops_sold,
            'day_night_time': self.renderer.day_night.time_of_day,
            'fields': [f.to_dict() for f in self.fields],
            'vehicles': [v.to_dict() for v in self.vehicles],
            'workers': [w.to_dict() for w in self.workers],
            'economy': self.economy.to_dict(),
            'weather': self.weather.to_dict(),
            'events': self.events.to_dict(),
        }

    def load_from_dict(self, data: dict):
        """Load world state from save data."""
        self.playtime = data.get('playtime', 0)
        self.farm_level = data.get('farm_level', 1)
        self.farm_xp = data.get('farm_xp', 0)
        self.farm_xp_to_next = data.get('farm_xp_to_next', 500)
        self.total_harvests = data.get('total_harvests', 0)
        self.total_crops_sold = data.get('total_crops_sold', 0)

        if 'day_night_time' in data:
            self.renderer.day_night.time_of_day = data['day_night_time']

        # Load entities
        self.fields = [Field.from_dict(fd) for fd in data.get('fields', [])]
        self.vehicles = [Vehicle.from_dict(vd) for vd in data.get('vehicles', [])]
        self.workers = [Worker.from_dict(wd) for wd in data.get('workers', [])]

        if 'economy' in data:
            self.economy = Economy.from_dict(data['economy'])
        if 'weather' in data:
            self.weather = WeatherSystem.from_dict(data['weather'])
        if 'events' in data:
            self.events = EventSystem.from_dict(data['events'])

        # Recreate animals
        self.dog = FarmDog(self.farmhouse_x + 20, self.ground_y + 5)
        self.cat = FarmCat(self.barn_x + 10, self.ground_y - 30)

        self._update_world_width()
        logger.info(f"World loaded: {len(self.fields)} fields, "
                    f"{len(self.vehicles)} vehicles, {len(self.workers)} workers")
