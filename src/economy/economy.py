"""
Economy system - money, market prices, storage, transactions.
"""
import logging
import random
from typing import Dict, List, Any

from src.core.constants import STARTING_MONEY, STARTING_FUEL

logger = logging.getLogger("economy")


class MarketPrices:
    """Manages fluctuating market prices for crops."""

    def __init__(self):
        self.base_prices = {
            'wheat': 35, 'barley': 30, 'corn': 45,
            'sunflower': 55, 'potato': 25, 'canola': 60, 'peas': 40,
        }
        self.current_prices: Dict[str, float] = {}
        self.price_history: Dict[str, List[float]] = {}
        self._fluctuation_timer = 0.0

        # Initialize
        for crop, base in self.base_prices.items():
            self.current_prices[crop] = base
            self.price_history[crop] = [base]

    def update(self, dt: float):
        """Update market prices with gentle fluctuation."""
        self._fluctuation_timer += dt
        if self._fluctuation_timer >= 120:  # Every 2 minutes
            self._fluctuation_timer = 0
            for crop, base in self.base_prices.items():
                change = random.uniform(-0.08, 0.08)
                new_price = self.current_prices[crop] * (1 + change)
                # Clamp to ±30% of base
                new_price = max(base * 0.7, min(base * 1.3, new_price))
                self.current_prices[crop] = round(new_price, 1)
                self.price_history[crop].append(self.current_prices[crop])
                # Keep last 20 prices
                if len(self.price_history[crop]) > 20:
                    self.price_history[crop] = self.price_history[crop][-20:]

    def get_price(self, crop: str, quality_modifier: float = 1.0) -> float:
        return self.current_prices.get(crop, 30) * quality_modifier

    def to_dict(self) -> dict:
        return {
            'current_prices': dict(self.current_prices),
            'price_history': {k: list(v) for k, v in self.price_history.items()},
        }

    @staticmethod
    def from_dict(data: dict) -> 'MarketPrices':
        mp = MarketPrices()
        mp.current_prices = data.get('current_prices', mp.current_prices)
        mp.price_history = data.get('price_history', mp.price_history)
        return mp


class Storage:
    """Farm storage for harvested crops."""

    def __init__(self, capacity: float = 2000):
        self.capacity = capacity
        self.contents: Dict[str, float] = {}

    def add(self, crop: str, amount: float) -> float:
        """Add crop to storage. Returns amount actually stored."""
        current_total = sum(self.contents.values())
        available = self.capacity - current_total
        stored = min(amount, available)

        if stored > 0:
            self.contents[crop] = self.contents.get(crop, 0) + stored

        return stored

    def remove(self, crop: str, amount: float) -> float:
        """Remove crop from storage. Returns amount actually removed."""
        available = self.contents.get(crop, 0)
        removed = min(amount, available)
        if removed > 0:
            self.contents[crop] -= removed
            if self.contents[crop] <= 0:
                del self.contents[crop]
        return removed

    @property
    def total_stored(self) -> float:
        return sum(self.contents.values())

    @property
    def fill_percentage(self) -> float:
        return (self.total_stored / self.capacity * 100) if self.capacity > 0 else 0

    def to_dict(self) -> dict:
        return {
            'capacity': self.capacity,
            'contents': dict(self.contents),
        }

    @staticmethod
    def from_dict(data: dict) -> 'Storage':
        s = Storage(data.get('capacity', 2000))
        s.contents = data.get('contents', {})
        return s


class Economy:
    """Main economy manager."""

    def __init__(self):
        self.money = STARTING_MONEY
        self.fuel = STARTING_FUEL
        self.total_earned = 0
        self.total_spent = 0
        self.total_harvested = 0.0
        self.market = MarketPrices()
        self.storage = Storage()

        # Transaction log (last 50)
        self.transactions: List[Dict[str, Any]] = []

        # Auto-sell settings
        self.auto_sell = "never"  # never, always, threshold, price
        self.auto_sell_threshold = 80  # % storage
        self.auto_sell_min_price = 0

    def earn(self, amount: float, reason: str = ""):
        """Add money."""
        self.money += amount
        self.total_earned += amount
        self._log_transaction("income", amount, reason)

    def spend(self, amount: float, reason: str = "") -> bool:
        """Spend money. Returns False if insufficient funds."""
        if self.money >= amount:
            self.money -= amount
            self.total_spent += amount
            self._log_transaction("expense", amount, reason)
            return True
        return False

    def can_afford(self, amount: float) -> bool:
        return self.money >= amount

    def sell_crop(self, crop: str, amount: float, quality: float = 50) -> float:
        """Sell crop from storage. Returns money earned."""
        from src.crops.crop_data import get_quality_price_modifier
        actual = self.storage.remove(crop, amount)
        if actual > 0:
            quality_mod = get_quality_price_modifier(quality)
            price = self.market.get_price(crop, quality_mod)
            total = actual * price / 100  # Price per 100kg
            self.earn(total, f"Sold {actual:.0f}kg {crop}")
            return total
        return 0

    def sell_all(self, crop: str = None) -> float:
        """Sell all of one crop or all crops."""
        total = 0
        if crop:
            amount = self.storage.contents.get(crop, 0)
            if amount > 0:
                total = self.sell_crop(crop, amount)
        else:
            for c in list(self.storage.contents.keys()):
                amount = self.storage.contents.get(c, 0)
                if amount > 0:
                    total += self.sell_crop(c, amount)
        return total

    def check_auto_sell(self):
        """Check and execute auto-sell if conditions met."""
        if self.auto_sell == "never":
            return
        elif self.auto_sell == "always":
            self.sell_all()
        elif self.auto_sell == "threshold":
            if self.storage.fill_percentage >= self.auto_sell_threshold:
                self.sell_all()
        elif self.auto_sell == "price":
            for crop in list(self.storage.contents.keys()):
                if self.market.current_prices.get(crop, 0) >= self.auto_sell_min_price:
                    self.sell_crop(crop, self.storage.contents.get(crop, 0))

    def use_fuel(self, amount: float) -> bool:
        """Use fuel. Returns False if insufficient."""
        if self.fuel >= amount:
            self.fuel -= amount
            return True
        return False

    def buy_fuel(self, amount: float, price_per_unit: float = 2.0) -> bool:
        """Buy fuel."""
        cost = amount * price_per_unit
        if self.spend(cost, f"Fuel: {amount:.0f}L"):
            self.fuel += amount
            return True
        return False

    def update(self, dt: float):
        """Update economy (market prices, auto-sell)."""
        self.market.update(dt)
        self.check_auto_sell()

    def _log_transaction(self, ttype: str, amount: float, reason: str):
        self.transactions.append({
            'type': ttype, 'amount': round(amount, 2), 'reason': reason
        })
        if len(self.transactions) > 50:
            self.transactions = self.transactions[-50:]

    def to_dict(self) -> dict:
        return {
            'money': round(self.money, 2),
            'fuel': round(self.fuel, 2),
            'total_earned': round(self.total_earned, 2),
            'total_spent': round(self.total_spent, 2),
            'total_harvested': round(self.total_harvested, 2),
            'market': self.market.to_dict(),
            'storage': self.storage.to_dict(),
            'auto_sell': self.auto_sell,
            'auto_sell_threshold': self.auto_sell_threshold,
            'auto_sell_min_price': self.auto_sell_min_price,
        }

    @staticmethod
    def from_dict(data: dict) -> 'Economy':
        e = Economy()
        e.money = data.get('money', STARTING_MONEY)
        e.fuel = data.get('fuel', STARTING_FUEL)
        e.total_earned = data.get('total_earned', 0)
        e.total_spent = data.get('total_spent', 0)
        e.total_harvested = data.get('total_harvested', 0)
        if 'market' in data:
            e.market = MarketPrices.from_dict(data['market'])
        if 'storage' in data:
            e.storage = Storage.from_dict(data['storage'])
        e.auto_sell = data.get('auto_sell', 'never')
        e.auto_sell_threshold = data.get('auto_sell_threshold', 80)
        e.auto_sell_min_price = data.get('auto_sell_min_price', 0)
        return e
