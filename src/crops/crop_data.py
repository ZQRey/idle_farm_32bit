"""
Crop definitions and data.
"""
from typing import Dict, Any


CROP_DATA: Dict[str, Dict[str, Any]] = {
    "wheat": {
        "name": "Wheat",
        "growth_time": 1080,  # seconds (18 min)
        "base_yield": 250,  # kg per field
        "seed_cost": 50,
        "water_demand": 0.5,
        "heat_resistance": 0.6,
        "cold_resistance": 0.7,
        "hail_resistance": 0.4,
        "base_price": 35,
        "sprite_folder": "crops/wheat",
    },
    "barley": {
        "name": "Barley",
        "growth_time": 960,
        "base_yield": 200,
        "seed_cost": 40,
        "water_demand": 0.4,
        "heat_resistance": 0.7,
        "cold_resistance": 0.8,
        "hail_resistance": 0.5,
        "base_price": 30,
        "sprite_folder": "crops/barley",
    },
    "corn": {
        "name": "Corn",
        "growth_time": 1320,
        "base_yield": 350,
        "seed_cost": 80,
        "water_demand": 0.7,
        "heat_resistance": 0.8,
        "cold_resistance": 0.3,
        "hail_resistance": 0.3,
        "base_price": 45,
        "sprite_folder": "crops/corn",
    },
    "sunflower": {
        "name": "Sunflower",
        "growth_time": 1200,
        "base_yield": 180,
        "seed_cost": 60,
        "water_demand": 0.5,
        "heat_resistance": 0.9,
        "cold_resistance": 0.4,
        "hail_resistance": 0.3,
        "base_price": 55,
        "sprite_folder": "crops/sunflower",
    },
    "potato": {
        "name": "Potato",
        "growth_time": 1500,
        "base_yield": 400,
        "seed_cost": 70,
        "water_demand": 0.6,
        "heat_resistance": 0.5,
        "cold_resistance": 0.6,
        "hail_resistance": 0.8,
        "base_price": 25,
        "sprite_folder": "crops/wheat",  # reuse for now
    },
    "canola": {
        "name": "Canola",
        "growth_time": 1080,
        "base_yield": 150,
        "seed_cost": 55,
        "water_demand": 0.5,
        "heat_resistance": 0.5,
        "cold_resistance": 0.6,
        "hail_resistance": 0.4,
        "base_price": 60,
        "sprite_folder": "crops/wheat",
    },
    "peas": {
        "name": "Peas",
        "growth_time": 900,
        "base_yield": 120,
        "seed_cost": 35,
        "water_demand": 0.6,
        "heat_resistance": 0.4,
        "cold_resistance": 0.7,
        "hail_resistance": 0.5,
        "base_price": 40,
        "sprite_folder": "crops/wheat",
    },
}


def get_quality_name(quality: float) -> str:
    """Get quality category from 0-100 quality value."""
    if quality >= 90:
        return "premium"
    elif quality >= 75:
        return "excellent"
    elif quality >= 55:
        return "good"
    elif quality >= 35:
        return "normal"
    else:
        return "poor"


def get_quality_price_modifier(quality: float) -> float:
    """Get price modifier based on crop quality."""
    name = get_quality_name(quality)
    return {
        "premium": 1.5,
        "excellent": 1.3,
        "good": 1.1,
        "normal": 1.0,
        "poor": 0.7,
    }[name]


def calculate_yield(base_yield: float, fertility: float, moisture: float,
                    weather_mod: float, worker_mod: float, equipment_mod: float,
                    damage_mod: float) -> float:
    """Calculate actual yield using the yield formula."""
    result = (base_yield
              * max(0.1, fertility)
              * max(0.1, moisture)
              * max(0.1, weather_mod)
              * max(0.5, worker_mod)
              * max(0.5, equipment_mod)
              * max(0.1, 1.0 - damage_mod))
    return max(0, result)
