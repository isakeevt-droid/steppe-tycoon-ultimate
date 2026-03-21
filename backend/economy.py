from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import random

from .content import BUILDINGS, WORKERS, RESOURCES, TITLES, SETTINGS

MONEY_STEP = Decimal("0.01")


def money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_STEP, rounding=ROUND_HALF_UP)


def now_utc() -> datetime:
    return datetime.utcnow()


def get_day_key(dt: datetime | None = None) -> str:
    dt = dt or now_utc()
    return dt.strftime("%Y-%m-%d")


def calculate_storage_capacity(storage_level: int) -> float:
    return SETTINGS["start_storage"] * (1 + (storage_level - 1) * SETTINGS["storage_capacity_multiplier"])


def calculate_storage_upgrade_cost(storage_level: int) -> Decimal:
    return money(SETTINGS["storage_upgrade_base_cost"] * (SETTINGS["storage_upgrade_growth"] ** (storage_level - 1)))


def calculate_building_price(building_key: str, owned: int) -> Decimal:
    item = BUILDINGS[building_key]
    return money(item["base_price"] * (item["price_growth"] ** owned))


def calculate_worker_hire_cost(worker_key: str) -> Decimal:
    return money(WORKERS[worker_key]["hire_cost"])


def calculate_worker_bonus(worker_counts: dict[str, int]) -> float:
    total = 0.0
    for key, count in worker_counts.items():
        total += WORKERS[key]["efficiency_bonus"] * count
    return total


def calculate_worker_salary_per_minute(worker_counts: dict[str, int]) -> Decimal:
    total = Decimal("0")
    for key, count in worker_counts.items():
        total += Decimal(str(WORKERS[key]["salary_per_minute"])) * Decimal(count)
    return money(total)


def calculate_global_bonus_pct(achievement_bonus_pct: float, title_bonus_pct: float) -> float:
    return (achievement_bonus_pct + title_bonus_pct) / 100.0


def calculate_building_output_per_second(building_key: str, level: int, worker_bonus: float, global_bonus: float, payroll_ok: bool) -> float:
    if level <= 0:
        return 0.0
    item = BUILDINGS[building_key]
    if item["category"] != "production":
        return 0.0
    penalty = 1.0 if payroll_ok else 0.5
    per_cycle = item["base_output"] * level * (1 + worker_bonus) * (1 + global_bonus) * penalty
    return per_cycle / item["cycle_seconds"]


def calculate_processing_output_per_second(level: int, batch_size: float, worker_bonus: float, global_bonus: float, payroll_ok: bool) -> float:
    if level <= 0:
        return 0.0
    penalty = 1.0 if payroll_ok else 0.5
    return (batch_size * level * (1 + worker_bonus) * (1 + global_bonus) * penalty) / 120.0


def calculate_market_price(resource_key: str, market_seed: int) -> Decimal:
    base = Decimal(str(RESOURCES[resource_key]["base_price"]))
    random.seed(f"{resource_key}:{market_seed}")
    multiplier = Decimal(str(random.uniform(0.85, 1.15)))
    return money(base * multiplier)


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


def calculate_dirham_buy_price(bought_today: int) -> Decimal:
    return money(SETTINGS["dirham_price_base"] * (SETTINGS["dirham_price_growth"] ** bought_today))


def calculate_mine_crit_chance(pickaxe_level: int) -> float:
    return min(20.0, pickaxe_level * 1.5)


def calculate_mine_crit_multiplier(mine_level: int) -> float:
    return 1.5 + (mine_level - 1) * 0.06


def calculate_mine_click_income(level: int, pickaxe_level: int, achievement_bonus: float, title_bonus: float) -> tuple[Decimal, Decimal, float, float]:
    global_bonus = calculate_global_bonus_pct(achievement_bonus, title_bonus)
    base_tap = Decimal(str(SETTINGS["mine_click_base"])) * Decimal(str(1 + (level - 1) * 0.03)) * Decimal(str(1 + global_bonus))
    crit_chance = calculate_mine_crit_chance(pickaxe_level)
    crit_multiplier = calculate_mine_crit_multiplier(level)
    average_tap = base_tap * (Decimal("1") + (Decimal(str(crit_chance)) / Decimal("100")) * (Decimal(str(crit_multiplier)) - Decimal("1")))
    return money(base_tap), money(average_tap), round(crit_chance, 2), round(crit_multiplier, 2)


def calculate_mine_upgrade_cost(level: int) -> Decimal:
    return money(SETTINGS["mine_upgrade_cost_base"] * (SETTINGS["mine_upgrade_cost_growth"] ** (level - 1)))


def calculate_pickaxe_upgrade_cost(level: int) -> Decimal:
    return money(SETTINGS["mine_pickaxe_cost_base"] * (SETTINGS["mine_pickaxe_cost_growth"] ** level))


def calculate_auto_activation_cost(building_level: int) -> int:
    return max(1, 1 + (building_level // 10))
