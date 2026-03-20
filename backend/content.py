from __future__ import annotations

BUILDINGS = {
    "farm": {
        "name": "Ферма",
        "category": "production",
        "resource_key": "grain",
        "base_price": 60,
        "price_growth": 1.18,
        "base_output": 3.0,
        "cycle_seconds": 20,
        "description": "Выращивает зерно для продажи и переработки в муку.",
    },
    "pasture": {
        "name": "Пастбище",
        "category": "production",
        "resource_key": "wool",
        "base_price": 90,
        "price_growth": 1.18,
        "base_output": 2.0,
        "cycle_seconds": 20,
        "description": "Даёт шерсть для ткацкой.",
    },
    "lumbermill": {
        "name": "Лесопилка",
        "category": "production",
        "resource_key": "wood",
        "base_price": 130,
        "price_growth": 1.19,
        "base_output": 2.0,
        "cycle_seconds": 20,
        "description": "Производит древесину для продажи и столярной.",
    },
    "ore_mine": {
        "name": "Рудная шахта",
        "category": "production",
        "resource_key": "ore",
        "base_price": 180,
        "price_growth": 1.20,
        "base_output": 1.5,
        "cycle_seconds": 20,
        "description": "Добывает руду для кузни.",
    },
    "mill": {
        "name": "Мельница",
        "category": "processing",
        "input_key": "grain",
        "output_key": "flour",
        "batch_size": 10,
        "base_price": 220,
        "price_growth": 1.20,
        "description": "Перерабатывает зерно в муку.",
    },
    "weavery": {
        "name": "Ткацкая",
        "category": "processing",
        "input_key": "wool",
        "output_key": "cloth",
        "batch_size": 10,
        "base_price": 270,
        "price_growth": 1.20,
        "description": "Превращает шерсть в ткань.",
    },
    "carpentry": {
        "name": "Столярная",
        "category": "processing",
        "input_key": "wood",
        "output_key": "planks",
        "batch_size": 10,
        "base_price": 310,
        "price_growth": 1.21,
        "description": "Перерабатывает древесину в доски.",
    },
    "forge": {
        "name": "Кузня",
        "category": "processing",
        "input_key": "ore",
        "output_key": "metal",
        "batch_size": 10,
        "base_price": 340,
        "price_growth": 1.22,
        "description": "Выплавляет металл из руды.",
    },
}

WORKERS = {
    "novice": {
        "name": "Руки из кармана",
        "efficiency_bonus": 0.10,
        "salary_per_minute": 3.0,
        "hire_cost": 45,
        "description": "Дешёвый работник для старта.",
    },
    "worker": {
        "name": "Чуть шарю",
        "efficiency_bonus": 0.16,
        "salary_per_minute": 6.0,
        "hire_cost": 90,
        "description": "Базовый надёжный работник.",
    },
    "specialist": {
        "name": "Норм тип",
        "efficiency_bonus": 0.27,
        "salary_per_minute": 11.0,
        "hire_cost": 180,
        "description": "Сильный mid-game работник.",
    },
    "master": {
        "name": "Вообще опасный",
        "efficiency_bonus": 0.42,
        "salary_per_minute": 19.0,
        "hire_cost": 360,
        "description": "Лучший работник. Дорог в найме и содержании.",
    },
}

WORKER_UPGRADES = {
    "novice_to_worker": {"from": "novice", "to": "worker", "cost_dirhams": 1},
    "worker_to_specialist": {"from": "worker", "to": "specialist", "cost_dirhams": 2},
    "specialist_to_master": {"from": "specialist", "to": "master", "cost_dirhams": 4},
}

RESOURCES = {
    "grain": {"name": "Зерно", "base_price": 2.2, "kind": "raw"},
    "wool": {"name": "Шерсть", "base_price": 3.0, "kind": "raw"},
    "wood": {"name": "Древесина", "base_price": 3.8, "kind": "raw"},
    "ore": {"name": "Руда", "base_price": 5.0, "kind": "raw"},
    "flour": {"name": "Мука", "base_price": 3.5, "kind": "processed"},
    "cloth": {"name": "Ткань", "base_price": 5.4, "kind": "processed"},
    "planks": {"name": "Доски", "base_price": 5.7, "kind": "processed"},
    "metal": {"name": "Металл", "base_price": 10.0, "kind": "processed"},
}

PROCESSING_RECIPES = {
    "mill": {"building_key": "mill", "input_key": "grain", "output_key": "flour", "multiplier": 1.6},
    "weavery": {"building_key": "weavery", "input_key": "wool", "output_key": "cloth", "multiplier": 1.8},
    "carpentry": {"building_key": "carpentry", "input_key": "wood", "output_key": "planks", "multiplier": 1.5},
    "forge": {"building_key": "forge", "input_key": "ore", "output_key": "metal", "multiplier": 2.0},
}

CARAVAN_ROUTES = {
    "balasagun": {
        "name": "Баласагун",
        "duration_seconds": 600,
        "profit_bonus": 0.40,
        "risk_percent": 5.0,
        "bonus_type": "time_reduction",
        "bonus_value": 0.10,
    },
    "suyab": {
        "name": "Суяб",
        "duration_seconds": 900,
        "profit_bonus": 0.55,
        "risk_percent": 8.0,
        "bonus_type": "success_chance",
        "bonus_value": 0.05,
    },
    "taraz": {
        "name": "Тараз",
        "duration_seconds": 1500,
        "profit_bonus": 0.70,
        "risk_percent": 12.0,
        "bonus_type": "raw_bonus",
        "bonus_value": 0.10,
    },
    "fergana": {
        "name": "Фергана",
        "duration_seconds": 2400,
        "profit_bonus": 0.95,
        "risk_percent": 16.0,
        "bonus_type": "processed_bonus",
        "bonus_value": 0.12,
    },
    "samarkand": {
        "name": "Самарканд",
        "duration_seconds": 3600,
        "profit_bonus": 1.30,
        "risk_percent": 22.0,
        "bonus_type": "processed_bonus",
        "bonus_value": 0.15,
    },
    "bukhara": {
        "name": "Бухара",
        "duration_seconds": 4800,
        "profit_bonus": 1.60,
        "risk_percent": 28.0,
        "bonus_type": "gold_bonus",
        "bonus_value": 0.18,
    },
    "kashgar": {
        "name": "Кашгар",
        "duration_seconds": 7200,
        "profit_bonus": 2.00,
        "risk_percent": 35.0,
        "bonus_type": "dirham_chance",
        "bonus_value": 0.12,
    },
}

GUARDS = {
    "none": {"name": "Без охраны", "cost_dirhams": 0, "risk_reduction": 0.0},
    "basic": {"name": "Базовая", "cost_dirhams": 1, "risk_reduction": 15.0},
    "experienced": {"name": "Опытная", "cost_dirhams": 2, "risk_reduction": 25.0},
    "elite": {"name": "Элитная", "cost_dirhams": 4, "risk_reduction": 100.0},
}

TITLES = [
    {"key": "nomad", "name": "Кочевник", "score": 1000, "bonus_pct": 2.0},
    {"key": "trader", "name": "Торговец", "score": 3000, "bonus_pct": 2.0},
    {"key": "merchant", "name": "Купец", "score": 8000, "bonus_pct": 2.0},
    {"key": "caravanner", "name": "Караванщик", "score": 20000, "bonus_pct": 3.0},
    {"key": "supplier", "name": "Поставщик", "score": 50000, "bonus_pct": 3.0},
    {"key": "trade_master", "name": "Мастер торговли", "score": 120000, "bonus_pct": 3.0},
    {"key": "steppe_magnate", "name": "Магнат степей", "score": 300000, "bonus_pct": 4.0},
    {"key": "trade_lord", "name": "Лорд торговли", "score": 700000, "bonus_pct": 4.0},
    {"key": "great_merchant", "name": "Великий купец", "score": 1500000, "bonus_pct": 4.0},
    {"key": "khan", "name": "Хан караванов", "score": 3000000, "bonus_pct": 5.0},
    {"key": "steppe_ruler", "name": "Повелитель степи", "score": 7000000, "bonus_pct": 5.0},
    {"key": "silk_legend", "name": "Легенда Шёлкового пути", "score": 15000000, "bonus_pct": 5.0},
]

# shorter achievement list for clarity and performance
ACHIEVEMENTS = [
    {"key": "gold_100", "name": "Первые деньги", "description": "Заработай 100 золота.", "stat": "total_gold_earned", "threshold": 100, "bonus_pct": 0.5},
    {"key": "gold_1000", "name": "Хороший старт", "description": "Заработай 1000 золота.", "stat": "total_gold_earned", "threshold": 1000, "bonus_pct": 0.5},
    {"key": "gold_10000", "name": "Богаче становится", "description": "Заработай 10000 золота.", "stat": "total_gold_earned", "threshold": 10000, "bonus_pct": 1.0},
    {"key": "prod_100", "name": "Производство 100", "description": "Произведи 100 единиц сырья.", "stat": "total_resources_produced", "threshold": 100, "bonus_pct": 0.5},
    {"key": "prod_1000", "name": "Производство 1000", "description": "Произведи 1000 единиц сырья.", "stat": "total_resources_produced", "threshold": 1000, "bonus_pct": 1.0},
    {"key": "proc_50", "name": "Переработка 50", "description": "Переработай 50 единиц сырья.", "stat": "total_resources_processed", "threshold": 50, "bonus_pct": 0.5},
    {"key": "proc_500", "name": "Переработка 500", "description": "Переработай 500 единиц сырья.", "stat": "total_resources_processed", "threshold": 500, "bonus_pct": 1.0},
    {"key": "caravan_1", "name": "Первый караван", "description": "Отправь 1 караван.", "stat": "total_caravans_sent", "threshold": 1, "bonus_pct": 0.5},
    {"key": "caravan_10", "name": "Караванщик", "description": "Отправь 10 караванов.", "stat": "total_caravans_sent", "threshold": 10, "bonus_pct": 1.0},
    {"key": "building_farm_3", "name": "Фермер", "description": "Подними ферму до 3 уровня.", "building_key": "farm", "threshold": 3, "bonus_pct": 0.5},
    {"key": "worker_worker_1", "name": "Первый работник", "description": "Найми работника уровня 'Чуть шарю'.", "worker_key": "worker", "threshold": 1, "bonus_pct": 0.5},
]

SETTINGS = {
    "start_gold": 120.0,
    "start_storage": 100.0,
    "storage_upgrade_base_cost": 150.0,
    "storage_upgrade_growth": 1.7,
    "storage_capacity_multiplier": 0.6,
    "mine_click_base": 1.0,
    "mine_upgrade_cost_base": 100.0,
    "mine_upgrade_cost_growth": 1.7,
    "mine_pickaxe_cost_base": 80.0,
    "mine_pickaxe_cost_growth": 1.65,
    "auto_hours": 8,
    "dirham_price_base": 1500.0,
    "dirham_price_growth": 1.40,
    "dirham_daily_limit": 6,
    "free_chest_cooldown_seconds": 4 * 3600,
    "max_active_caravans": 5,
}
