
from __future__ import annotations

from datetime import datetime, timezone
from math import floor
import random

from .content import BUILDINGS, WORKERS, RESOURCES, PROCESSING_RECIPES, TITLES, SETTINGS


def now_utc() -> datetime:
    return datetime.utcnow()


def get_day_key(dt: datetime | None = None) -> str:
    dt = dt or now_utc()
    return dt.strftime("%Y-%m-%d")


def calculate_storage_capacity(storage_level: int) -> float:
    return SETTINGS["start_storage"] * (1 + (storage_level - 1) * SETTINGS["storage_capacity_multiplier"])


def calculate_storage_upgrade_cost(storage_level: int) -> float:
    return SETTINGS["storage_upgrade_base_cost"] * (SETTINGS["storage_upgrade_growth"] ** (storage_level - 1))


def calculate_building_price(building_key: str, owned: int) -> float:
    item = BUILDINGS[building_key]
    return item["base_price"] * (item["price_growth"] ** owned)


def calculate_worker_hire_cost(worker_key: str) -> float:
    return WORKERS[worker_key]["hire_cost"]


def calculate_worker_bonus(worker_counts: dict[str, int]) -> float:
    total = 0.0
    for key, count in worker_counts.items():
        total += WORKERS[key]["efficiency_bonus"] * count
    return total


def calculate_worker_salary_per_minute(worker_counts: dict[str, int]) -> float:
    total = 0.0
    for key, count in worker_counts.items():
        total += WORKERS[key]["salary_per_minute"] * count
    return total


def calculate_global_bonus_pct(achievement_bonus_pct: float, title_bonus_pct: float) -> float:
    return (achievement_bonus_pct + title_bonus_pct) / 100.0


def calculate_building_output_per_second(
    building_key: str,
    level: int,
    worker_bonus: float,
    global_bonus: float,
    payroll_ok: bool,
) -> float:
    if level <= 0:
        return 0.0
    item = BUILDINGS[building_key]
    if item["category"] != "production":
        return 0.0
    penalty = 1.0 if payroll_ok else 0.5
    per_cycle = item["base_output"] * level * (1 + worker_bonus) * (1 + global_bonus) * penalty
    return per_cycle / item["cycle_seconds"]


def calculate_market_price(resource_key: str, market_seed: int) -> float:
    base = RESOURCES[resource_key]["base_price"]
    random.seed(f"{resource_key}:{market_seed}")
    multiplier = random.uniform(0.85, 1.15)
    return round(base * multiplier, 2)


def calculate_rank_score(player, total_building_levels: int, worker_count: int) -> float:
    return (
        player.total_gold_earned * 0.35
        + player.total_resources_processed * 0.25
        + player.total_caravan_profit * 0.20
        + total_building_levels * 0.10
        + worker_count * 0.05
        + player.total_dirhams_spent * 0.05
    )


def determine_title_key(score: float) -> str:
    current = TITLES[0]["key"]
    for item in TITLES:
        if score >= item["score"]:
            current = item["key"]
    return current


def get_title_bonus_pct(title_key: str) -> float:
    for item in TITLES:
        if item["key"] == title_key:
            return item["bonus_pct"]
    return 0.0


def get_next_title(title_key: str):
    found = False
    for item in TITLES:
        if found:
            return item
        if item["key"] == title_key:
            found = True
    return None


def calculate_dirham_buy_price(bought_today: int) -> float:
    return SETTINGS["dirham_price_base"] * (SETTINGS["dirham_price_growth"] ** bought_today)


def calculate_mine_click_income(level: int, achievement_bonus: float, title_bonus: float) -> float:
    global_bonus = calculate_global_bonus_pct(achievement_bonus, title_bonus)
    return SETTINGS["mine_click_base"] * (1 + (level - 1) * 0.05) * (1 + global_bonus)


def calculate_mine_upgrade_cost(level: int) -> float:
    return SETTINGS["mine_upgrade_cost_base"] * (SETTINGS["mine_upgrade_cost_growth"] ** (level - 1))
