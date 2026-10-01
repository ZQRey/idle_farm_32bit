"""
Comprehensive unit test suite for Desktop Idle Farm.
Tests core gameplay systems: economy, field simulation, crop growth, weather, AI, and save/load.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.economy.economy import Economy, Storage, MarketPrices
from src.fields.field import Field, FieldTile, TileState
from src.crops.crop_data import CROP_DATA, calculate_yield
from src.weather.weather_system import WeatherSystem, WeatherType
from src.entities.workers.worker import Worker, Profession, TaskType
from src.entities.vehicles.vehicle import Vehicle, VehicleType, VehicleState, AttachmentType
from src.ai.farm_ai import FarmAI
from src.world.game_world import GameWorld


class TestCropStorage(unittest.TestCase):
    def setUp(self):
        self.storage = Storage(capacity=1000.0)

    def test_add_and_retrieve(self):
        added = self.storage.add("wheat", 200.0)
        self.assertEqual(added, 200.0)
        self.assertEqual(self.storage.contents.get("wheat"), 200.0)
        self.assertEqual(self.storage.total_stored, 200.0)

    def test_capacity_limit(self):
        self.storage.add("wheat", 900.0)
        added = self.storage.add("corn", 200.0)
        self.assertEqual(added, 100.0)  # Only 100 fits
        self.assertEqual(self.storage.total_stored, 1000.0)
        self.assertEqual(self.storage.fill_percentage, 100.0)

    def test_remove(self):
        self.storage.add("wheat", 300.0)
        removed = self.storage.remove("wheat", 100.0)
        self.assertEqual(removed, 100.0)
        self.assertEqual(self.storage.contents.get("wheat"), 200.0)


class TestEconomy(unittest.TestCase):
    def setUp(self):
        self.economy = Economy()

    def test_earn_and_spend(self):
        initial = self.economy.money
        self.economy.earn(500.0, "Test Income")
        self.assertEqual(self.economy.money, initial + 500.0)
        self.assertTrue(self.economy.can_afford(300.0))
        spent = self.economy.spend(300.0, "Test Expense")
        self.assertTrue(spent)
        self.assertEqual(self.economy.money, initial + 200.0)

    def test_sell_crops(self):
        self.economy.storage.add("wheat", 200.0)
        initial_money = self.economy.money
        revenue = self.economy.sell_crop("wheat", 100.0)
        self.assertGreater(revenue, 0.0)
        self.assertEqual(self.economy.money, initial_money + revenue)


class TestFieldSimulation(unittest.TestCase):
    def setUp(self):
        self.field = Field(1, 450, 74, width=10, height=4, crop_type="wheat")

    def test_initial_state(self):
        self.assertEqual(len(self.field.tiles), 4)
        self.assertEqual(len(self.field.tiles[0]), 10)
        self.assertTrue(self.field.needs_plowing)
        self.assertFalse(self.field.is_ready_for_harvest)

    def test_tile_work_progression(self):
        tile = self.field.get_next_work_tile(TileState.UNTOUCHED)
        self.assertIsNotNone(tile)
        tile.state = TileState.PLOWED
        self.assertEqual(tile.state, TileState.PLOWED)

    def test_crop_growth(self):
        for row in self.field.tiles:
            for tile in row:
                tile.state = TileState.SEEDED
                tile.crop_type = "wheat"
                tile.growth_progress = 0.0

        # Simulate growth ticks
        self.field.update_growth(50.0, weather_modifier=1.0)
        # Verify growth progressed
        for row in self.field.tiles:
            for tile in row:
                self.assertGreater(tile.growth_progress, 0.0)

    def test_yield_calculation(self):
        crop = CROP_DATA['wheat']
        total_yield = calculate_yield(
            crop['base_yield'],
            fertility=0.8,
            moisture=0.6,
            weather_mod=1.0,
            worker_mod=1.0,
            equipment_mod=1.0,
            damage_mod=0.0
        )
        self.assertGreater(total_yield, 0.0)


class TestWeatherSystem(unittest.TestCase):
    def setUp(self):
        self.weather = WeatherSystem()

    def test_initial_weather(self):
        self.assertIn(self.weather.current, list(WeatherType))
        self.assertGreater(self.weather.duration, 0.0)

    def test_wind_speed_property(self):
        self.assertGreater(self.weather.wind_speed, 0.0)

    def test_modifiers(self):
        self.assertGreater(self.weather.work_speed_modifier, 0.0)
        self.assertGreater(self.weather.growth_modifier, 0.0)


class TestFarmAI(unittest.TestCase):
    def setUp(self):
        self.ai = FarmAI()
        self.economy = Economy()
        self.field = Field(1, 450, 74, width=5, height=2, crop_type="wheat")
        self.worker = Worker(Profession.TRACTOR_DRIVER)
        self.vehicle = Vehicle(VehicleType.SMALL_TRACTOR, 200, 115)

    def test_ai_task_generation(self):
        tasks = self.ai._generate_tasks([self.field], [self.vehicle], self.economy)
        self.assertTrue(any(t['type'] == TaskType.PLOW_FIELD for t in tasks))

    def test_worker_assignment(self):
        self.ai.update(5.0, [self.worker], [self.vehicle], [self.field], self.economy)
        # Worker should receive a plowing task
        self.assertEqual(self.worker.current_task, TaskType.PLOW_FIELD)


class TestWorldSerialization(unittest.TestCase):
    def test_world_save_and_load(self):
        world1 = GameWorld(1920, 180)
        world1.setup_new_game()
        world1.farm_level = 3
        world1.farm_xp = 180
        world1.economy.money = 7450.0

        save_data = world1.to_dict()
        self.assertIsInstance(save_data, dict)
        self.assertEqual(save_data['farm_level'], 3)
        self.assertEqual(save_data['farm_xp'], 180)

        world2 = GameWorld(1920, 180)
        world2.load_from_dict(save_data)
        self.assertEqual(world2.farm_level, 3)
        self.assertEqual(world2.farm_xp, 180)
        self.assertEqual(world2.economy.money, 7450.0
)
        self.assertEqual(len(world2.fields), len(world1.fields))


if __name__ == '__main__':
    unittest.main()
