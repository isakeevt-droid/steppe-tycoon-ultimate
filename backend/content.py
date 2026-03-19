
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
        "description": "Выращивает зерно. Базовая и дешёвая производственная цепочка.",
    },
    "pasture": {
        "name": "Пастбище",
        "category": "production",
        "resource_key": "wool",
        "base_price": 90,
        "price_growth": 1.18,
        "base_output": 2.0,
        "cycle_seconds": 20,
        "description": "Даёт шерсть для дальнейшей переработки в ткань.",
    },
    "lumbermill": {
        "name": "Лесопилка",
        "category": "production",
        "resource_key": "wood",
        "base_price": 130,
        "price_growth": 1.19,
        "base_output": 2.0,
        "cycle_seconds": 20,
        "description": "Производит древесину. Основа для досок.",
    },
    "ore_mine": {
        "name": "Рудная шахта",
        "category": "production",
        "resource_key": "ore",
        "base_price": 180,
        "price_growth": 1.20,
        "base_output": 1.5,
        "cycle_seconds": 20,
        "description": "Добывает руду для выплавки металла.",
    },
    "mill": {
        "name": "Мельница",
        "category": "processing",
        "input_key": "grain",
        "output_key": "flour",
        "batch_size": 10,
        "base_price": 220,
        "price_growth": 1.20,
        "description": "Перерабатывает зерно в муку. Выгоднее прямой продажи сырья.",
    },
    "weavery": {
        "name": "Ткацкая",
        "category": "processing",
        "input_key": "wool",
        "output_key": "cloth",
        "batch_size": 10,
        "base_price": 270,
        "price_growth": 1.20,
        "description": "Превращает шерсть в ткань с высокой добавленной стоимостью.",
    },
    "forge": {
        "name": "Кузня",
        "category": "processing",
        "input_key": "ore",
        "output_key": "metal",
        "batch_size": 10,
        "base_price": 340,
        "price_growth": 1.22,
        "description": "Выплавляет металл. Медленнее, но очень выгодно.",
    },
}

WORKERS = {
    "novice": {
        "name": "новичек Руки из кармана",
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
    "mill": {"input_key": "grain", "output_key": "flour", "multiplier": 1.6},
    "weavery": {"input_key": "wool", "output_key": "cloth", "multiplier": 1.8},
    "sawmill_process": {"input_key": "wood", "output_key": "planks", "multiplier": 1.5},
    "forge": {"input_key": "ore", "output_key": "metal", "multiplier": 2.0},
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

ACHIEVEMENTS = [
    {
        "key": "gold_100",
        "name": "Золото 100",
        "description": "Заработайте 100 ед.",
        "stat": "total_gold_earned",
        "threshold": 100,
        "bonus_pct": 0.5
    },
    {
        "key": "gold_250",
        "name": "Золото 250",
        "description": "Заработайте 250 ед.",
        "stat": "total_gold_earned",
        "threshold": 250,
        "bonus_pct": 0.5
    },
    {
        "key": "gold_500",
        "name": "Золото 500",
        "description": "Заработайте 500 ед.",
        "stat": "total_gold_earned",
        "threshold": 500,
        "bonus_pct": 0.5
    },
    {
        "key": "gold_1000",
        "name": "Золото 1000",
        "description": "Заработайте 1000 ед.",
        "stat": "total_gold_earned",
        "threshold": 1000,
        "bonus_pct": 0.5
    },
    {
        "key": "gold_2500",
        "name": "Золото 2500",
        "description": "Заработайте 2500 ед.",
        "stat": "total_gold_earned",
        "threshold": 2500,
        "bonus_pct": 0.5
    },
    {
        "key": "gold_5000",
        "name": "Золото 5000",
        "description": "Заработайте 5000 ед.",
        "stat": "total_gold_earned",
        "threshold": 5000,
        "bonus_pct": 0.5
    },
    {
        "key": "gold_10000",
        "name": "Золото 10000",
        "description": "Заработайте 10000 ед.",
        "stat": "total_gold_earned",
        "threshold": 10000,
        "bonus_pct": 0.5
    },
    {
        "key": "gold_25000",
        "name": "Золото 25000",
        "description": "Заработайте 25000 ед.",
        "stat": "total_gold_earned",
        "threshold": 25000,
        "bonus_pct": 0.5
    },
    {
        "key": "gold_50000",
        "name": "Золото 50000",
        "description": "Заработайте 50000 ед.",
        "stat": "total_gold_earned",
        "threshold": 50000,
        "bonus_pct": 0.5
    },
    {
        "key": "gold_100000",
        "name": "Золото 100000",
        "description": "Заработайте 100000 ед.",
        "stat": "total_gold_earned",
        "threshold": 100000,
        "bonus_pct": 0.5
    },
    {
        "key": "gold_250000",
        "name": "Золото 250000",
        "description": "Заработайте 250000 ед.",
        "stat": "total_gold_earned",
        "threshold": 250000,
        "bonus_pct": 0.5
    },
    {
        "key": "gold_500000",
        "name": "Золото 500000",
        "description": "Заработайте 500000 ед.",
        "stat": "total_gold_earned",
        "threshold": 500000,
        "bonus_pct": 0.5
    },
    {
        "key": "gold_1000000",
        "name": "Золото 1000000",
        "description": "Заработайте 1000000 ед.",
        "stat": "total_gold_earned",
        "threshold": 1000000,
        "bonus_pct": 0.5
    },
    {
        "key": "gold_2500000",
        "name": "Золото 2500000",
        "description": "Заработайте 2500000 ед.",
        "stat": "total_gold_earned",
        "threshold": 2500000,
        "bonus_pct": 0.5
    },
    {
        "key": "gold_5000000",
        "name": "Золото 5000000",
        "description": "Заработайте 5000000 ед.",
        "stat": "total_gold_earned",
        "threshold": 5000000,
        "bonus_pct": 0.5
    },
    {
        "key": "prod_100",
        "name": "Производство 100",
        "description": "Произведите 100 ед.",
        "stat": "total_resources_produced",
        "threshold": 100,
        "bonus_pct": 0.5
    },
    {
        "key": "prod_250",
        "name": "Производство 250",
        "description": "Произведите 250 ед.",
        "stat": "total_resources_produced",
        "threshold": 250,
        "bonus_pct": 0.5
    },
    {
        "key": "prod_500",
        "name": "Производство 500",
        "description": "Произведите 500 ед.",
        "stat": "total_resources_produced",
        "threshold": 500,
        "bonus_pct": 0.5
    },
    {
        "key": "prod_1000",
        "name": "Производство 1000",
        "description": "Произведите 1000 ед.",
        "stat": "total_resources_produced",
        "threshold": 1000,
        "bonus_pct": 0.5
    },
    {
        "key": "prod_2500",
        "name": "Производство 2500",
        "description": "Произведите 2500 ед.",
        "stat": "total_resources_produced",
        "threshold": 2500,
        "bonus_pct": 0.5
    },
    {
        "key": "prod_5000",
        "name": "Производство 5000",
        "description": "Произведите 5000 ед.",
        "stat": "total_resources_produced",
        "threshold": 5000,
        "bonus_pct": 0.5
    },
    {
        "key": "prod_10000",
        "name": "Производство 10000",
        "description": "Произведите 10000 ед.",
        "stat": "total_resources_produced",
        "threshold": 10000,
        "bonus_pct": 0.5
    },
    {
        "key": "prod_25000",
        "name": "Производство 25000",
        "description": "Произведите 25000 ед.",
        "stat": "total_resources_produced",
        "threshold": 25000,
        "bonus_pct": 0.5
    },
    {
        "key": "prod_50000",
        "name": "Производство 50000",
        "description": "Произведите 50000 ед.",
        "stat": "total_resources_produced",
        "threshold": 50000,
        "bonus_pct": 0.5
    },
    {
        "key": "prod_100000",
        "name": "Производство 100000",
        "description": "Произведите 100000 ед.",
        "stat": "total_resources_produced",
        "threshold": 100000,
        "bonus_pct": 0.5
    },
    {
        "key": "prod_250000",
        "name": "Производство 250000",
        "description": "Произведите 250000 ед.",
        "stat": "total_resources_produced",
        "threshold": 250000,
        "bonus_pct": 0.5
    },
    {
        "key": "prod_500000",
        "name": "Производство 500000",
        "description": "Произведите 500000 ед.",
        "stat": "total_resources_produced",
        "threshold": 500000,
        "bonus_pct": 0.5
    },
    {
        "key": "prod_1000000",
        "name": "Производство 1000000",
        "description": "Произведите 1000000 ед.",
        "stat": "total_resources_produced",
        "threshold": 1000000,
        "bonus_pct": 0.5
    },
    {
        "key": "proc_25",
        "name": "Переработка 25",
        "description": "Переработайте 25 ед.",
        "stat": "total_resources_processed",
        "threshold": 25,
        "bonus_pct": 0.5
    },
    {
        "key": "proc_50",
        "name": "Переработка 50",
        "description": "Переработайте 50 ед.",
        "stat": "total_resources_processed",
        "threshold": 50,
        "bonus_pct": 0.5
    },
    {
        "key": "proc_100",
        "name": "Переработка 100",
        "description": "Переработайте 100 ед.",
        "stat": "total_resources_processed",
        "threshold": 100,
        "bonus_pct": 0.5
    },
    {
        "key": "proc_250",
        "name": "Переработка 250",
        "description": "Переработайте 250 ед.",
        "stat": "total_resources_processed",
        "threshold": 250,
        "bonus_pct": 0.5
    },
    {
        "key": "proc_500",
        "name": "Переработка 500",
        "description": "Переработайте 500 ед.",
        "stat": "total_resources_processed",
        "threshold": 500,
        "bonus_pct": 0.5
    },
    {
        "key": "proc_1000",
        "name": "Переработка 1000",
        "description": "Переработайте 1000 ед.",
        "stat": "total_resources_processed",
        "threshold": 1000,
        "bonus_pct": 0.5
    },
    {
        "key": "proc_2500",
        "name": "Переработка 2500",
        "description": "Переработайте 2500 ед.",
        "stat": "total_resources_processed",
        "threshold": 2500,
        "bonus_pct": 0.5
    },
    {
        "key": "proc_5000",
        "name": "Переработка 5000",
        "description": "Переработайте 5000 ед.",
        "stat": "total_resources_processed",
        "threshold": 5000,
        "bonus_pct": 0.5
    },
    {
        "key": "proc_10000",
        "name": "Переработка 10000",
        "description": "Переработайте 10000 ед.",
        "stat": "total_resources_processed",
        "threshold": 10000,
        "bonus_pct": 0.5
    },
    {
        "key": "proc_25000",
        "name": "Переработка 25000",
        "description": "Переработайте 25000 ед.",
        "stat": "total_resources_processed",
        "threshold": 25000,
        "bonus_pct": 0.5
    },
    {
        "key": "proc_50000",
        "name": "Переработка 50000",
        "description": "Переработайте 50000 ед.",
        "stat": "total_resources_processed",
        "threshold": 50000,
        "bonus_pct": 0.5
    },
    {
        "key": "car_1",
        "name": "Караваны 1",
        "description": "Отправьте 1 ед.",
        "stat": "total_caravans_sent",
        "threshold": 1,
        "bonus_pct": 0.5
    },
    {
        "key": "car_3",
        "name": "Караваны 3",
        "description": "Отправьте 3 ед.",
        "stat": "total_caravans_sent",
        "threshold": 3,
        "bonus_pct": 0.75
    },
    {
        "key": "car_5",
        "name": "Караваны 5",
        "description": "Отправьте 5 ед.",
        "stat": "total_caravans_sent",
        "threshold": 5,
        "bonus_pct": 0.75
    },
    {
        "key": "car_10",
        "name": "Караваны 10",
        "description": "Отправьте 10 ед.",
        "stat": "total_caravans_sent",
        "threshold": 10,
        "bonus_pct": 0.75
    },
    {
        "key": "car_20",
        "name": "Караваны 20",
        "description": "Отправьте 20 ед.",
        "stat": "total_caravans_sent",
        "threshold": 20,
        "bonus_pct": 0.75
    },
    {
        "key": "car_35",
        "name": "Караваны 35",
        "description": "Отправьте 35 ед.",
        "stat": "total_caravans_sent",
        "threshold": 35,
        "bonus_pct": 0.75
    },
    {
        "key": "car_50",
        "name": "Караваны 50",
        "description": "Отправьте 50 ед.",
        "stat": "total_caravans_sent",
        "threshold": 50,
        "bonus_pct": 0.75
    },
    {
        "key": "car_75",
        "name": "Караваны 75",
        "description": "Отправьте 75 ед.",
        "stat": "total_caravans_sent",
        "threshold": 75,
        "bonus_pct": 0.75
    },
    {
        "key": "car_100",
        "name": "Караваны 100",
        "description": "Отправьте 100 ед.",
        "stat": "total_caravans_sent",
        "threshold": 100,
        "bonus_pct": 0.75
    },
    {
        "key": "car_150",
        "name": "Караваны 150",
        "description": "Отправьте 150 ед.",
        "stat": "total_caravans_sent",
        "threshold": 150,
        "bonus_pct": 0.75
    },
    {
        "key": "car_200",
        "name": "Караваны 200",
        "description": "Отправьте 200 ед.",
        "stat": "total_caravans_sent",
        "threshold": 200,
        "bonus_pct": 0.75
    },
    {
        "key": "suc_1",
        "name": "Успешные караваны 1",
        "description": "Успешно завершите 1 ед.",
        "stat": "total_caravans_success",
        "threshold": 1,
        "bonus_pct": 0.75
    },
    {
        "key": "suc_3",
        "name": "Успешные караваны 3",
        "description": "Успешно завершите 3 ед.",
        "stat": "total_caravans_success",
        "threshold": 3,
        "bonus_pct": 0.75
    },
    {
        "key": "suc_5",
        "name": "Успешные караваны 5",
        "description": "Успешно завершите 5 ед.",
        "stat": "total_caravans_success",
        "threshold": 5,
        "bonus_pct": 0.75
    },
    {
        "key": "suc_10",
        "name": "Успешные караваны 10",
        "description": "Успешно завершите 10 ед.",
        "stat": "total_caravans_success",
        "threshold": 10,
        "bonus_pct": 0.75
    },
    {
        "key": "suc_20",
        "name": "Успешные караваны 20",
        "description": "Успешно завершите 20 ед.",
        "stat": "total_caravans_success",
        "threshold": 20,
        "bonus_pct": 0.75
    },
    {
        "key": "suc_35",
        "name": "Успешные караваны 35",
        "description": "Успешно завершите 35 ед.",
        "stat": "total_caravans_success",
        "threshold": 35,
        "bonus_pct": 0.75
    },
    {
        "key": "suc_50",
        "name": "Успешные караваны 50",
        "description": "Успешно завершите 50 ед.",
        "stat": "total_caravans_success",
        "threshold": 50,
        "bonus_pct": 0.75
    },
    {
        "key": "suc_75",
        "name": "Успешные караваны 75",
        "description": "Успешно завершите 75 ед.",
        "stat": "total_caravans_success",
        "threshold": 75,
        "bonus_pct": 0.75
    },
    {
        "key": "suc_100",
        "name": "Успешные караваны 100",
        "description": "Успешно завершите 100 ед.",
        "stat": "total_caravans_success",
        "threshold": 100,
        "bonus_pct": 0.75
    },
    {
        "key": "clk_10",
        "name": "Шахта 10",
        "description": "Сделайте 10 ед.",
        "stat": "total_clicks",
        "threshold": 10,
        "bonus_pct": 0.75
    },
    {
        "key": "clk_25",
        "name": "Шахта 25",
        "description": "Сделайте 25 ед.",
        "stat": "total_clicks",
        "threshold": 25,
        "bonus_pct": 0.75
    },
    {
        "key": "clk_50",
        "name": "Шахта 50",
        "description": "Сделайте 50 ед.",
        "stat": "total_clicks",
        "threshold": 50,
        "bonus_pct": 0.75
    },
    {
        "key": "clk_100",
        "name": "Шахта 100",
        "description": "Сделайте 100 ед.",
        "stat": "total_clicks",
        "threshold": 100,
        "bonus_pct": 0.75
    },
    {
        "key": "clk_250",
        "name": "Шахта 250",
        "description": "Сделайте 250 ед.",
        "stat": "total_clicks",
        "threshold": 250,
        "bonus_pct": 0.75
    },
    {
        "key": "clk_500",
        "name": "Шахта 500",
        "description": "Сделайте 500 ед.",
        "stat": "total_clicks",
        "threshold": 500,
        "bonus_pct": 0.75
    },
    {
        "key": "clk_1000",
        "name": "Шахта 1000",
        "description": "Сделайте 1000 ед.",
        "stat": "total_clicks",
        "threshold": 1000,
        "bonus_pct": 0.75
    },
    {
        "key": "clk_2500",
        "name": "Шахта 2500",
        "description": "Сделайте 2500 ед.",
        "stat": "total_clicks",
        "threshold": 2500,
        "bonus_pct": 0.75
    },
    {
        "key": "clk_5000",
        "name": "Шахта 5000",
        "description": "Сделайте 5000 ед.",
        "stat": "total_clicks",
        "threshold": 5000,
        "bonus_pct": 0.75
    },
    {
        "key": "clk_10000",
        "name": "Шахта 10000",
        "description": "Сделайте 10000 ед.",
        "stat": "total_clicks",
        "threshold": 10000,
        "bonus_pct": 0.75
    },
    {
        "key": "dir_1",
        "name": "Дирхамы куплены 1",
        "description": "Купите 1 ед.",
        "stat": "total_dirhams_bought",
        "threshold": 1,
        "bonus_pct": 0.75
    },
    {
        "key": "dir_2",
        "name": "Дирхамы куплены 2",
        "description": "Купите 2 ед.",
        "stat": "total_dirhams_bought",
        "threshold": 2,
        "bonus_pct": 0.75
    },
    {
        "key": "dir_3",
        "name": "Дирхамы куплены 3",
        "description": "Купите 3 ед.",
        "stat": "total_dirhams_bought",
        "threshold": 3,
        "bonus_pct": 0.75
    },
    {
        "key": "dir_5",
        "name": "Дирхамы куплены 5",
        "description": "Купите 5 ед.",
        "stat": "total_dirhams_bought",
        "threshold": 5,
        "bonus_pct": 0.75
    },
    {
        "key": "dir_8",
        "name": "Дирхамы куплены 8",
        "description": "Купите 8 ед.",
        "stat": "total_dirhams_bought",
        "threshold": 8,
        "bonus_pct": 0.75
    },
    {
        "key": "dir_12",
        "name": "Дирхамы куплены 12",
        "description": "Купите 12 ед.",
        "stat": "total_dirhams_bought",
        "threshold": 12,
        "bonus_pct": 0.75
    },
    {
        "key": "dsp_1",
        "name": "Дирхамы потрачены 1",
        "description": "Потратьте 1 ед.",
        "stat": "total_dirhams_spent",
        "threshold": 1,
        "bonus_pct": 0.75
    },
    {
        "key": "dsp_2",
        "name": "Дирхамы потрачены 2",
        "description": "Потратьте 2 ед.",
        "stat": "total_dirhams_spent",
        "threshold": 2,
        "bonus_pct": 0.75
    },
    {
        "key": "dsp_4",
        "name": "Дирхамы потрачены 4",
        "description": "Потратьте 4 ед.",
        "stat": "total_dirhams_spent",
        "threshold": 4,
        "bonus_pct": 0.75
    },
    {
        "key": "dsp_6",
        "name": "Дирхамы потрачены 6",
        "description": "Потратьте 6 ед.",
        "stat": "total_dirhams_spent",
        "threshold": 6,
        "bonus_pct": 0.75
    },
    {
        "key": "dsp_10",
        "name": "Дирхамы потрачены 10",
        "description": "Потратьте 10 ед.",
        "stat": "total_dirhams_spent",
        "threshold": 10,
        "bonus_pct": 0.75
    },
    {
        "key": "dsp_15",
        "name": "Дирхамы потрачены 15",
        "description": "Потратьте 15 ед.",
        "stat": "total_dirhams_spent",
        "threshold": 15,
        "bonus_pct": 0.75
    },
    {
        "key": "dsp_20",
        "name": "Дирхамы потрачены 20",
        "description": "Потратьте 20 ед.",
        "stat": "total_dirhams_spent",
        "threshold": 20,
        "bonus_pct": 0.75
    },
    {
        "key": "build_farm_1",
        "name": "Ферма 1",
        "description": "Постройте/улучшите ферма до 1 уровня.",
        "building_key": "farm",
        "threshold": 1,
        "bonus_pct": 0.5
    },
    {
        "key": "build_farm_3",
        "name": "Ферма 3",
        "description": "Постройте/улучшите ферма до 3 уровня.",
        "building_key": "farm",
        "threshold": 3,
        "bonus_pct": 0.5
    },
    {
        "key": "build_farm_5",
        "name": "Ферма 5",
        "description": "Постройте/улучшите ферма до 5 уровня.",
        "building_key": "farm",
        "threshold": 5,
        "bonus_pct": 0.5
    },
    {
        "key": "build_farm_10",
        "name": "Ферма 10",
        "description": "Постройте/улучшите ферма до 10 уровня.",
        "building_key": "farm",
        "threshold": 10,
        "bonus_pct": 0.5
    },
    {
        "key": "build_farm_20",
        "name": "Ферма 20",
        "description": "Постройте/улучшите ферма до 20 уровня.",
        "building_key": "farm",
        "threshold": 20,
        "bonus_pct": 0.5
    },
    {
        "key": "build_pasture_1",
        "name": "Пастбище 1",
        "description": "Постройте/улучшите пастбище до 1 уровня.",
        "building_key": "pasture",
        "threshold": 1,
        "bonus_pct": 0.5
    },
    {
        "key": "build_pasture_3",
        "name": "Пастбище 3",
        "description": "Постройте/улучшите пастбище до 3 уровня.",
        "building_key": "pasture",
        "threshold": 3,
        "bonus_pct": 0.5
    },
    {
        "key": "build_pasture_5",
        "name": "Пастбище 5",
        "description": "Постройте/улучшите пастбище до 5 уровня.",
        "building_key": "pasture",
        "threshold": 5,
        "bonus_pct": 0.5
    },
    {
        "key": "build_pasture_10",
        "name": "Пастбище 10",
        "description": "Постройте/улучшите пастбище до 10 уровня.",
        "building_key": "pasture",
        "threshold": 10,
        "bonus_pct": 0.5
    },
    {
        "key": "build_pasture_20",
        "name": "Пастбище 20",
        "description": "Постройте/улучшите пастбище до 20 уровня.",
        "building_key": "pasture",
        "threshold": 20,
        "bonus_pct": 0.5
    },
    {
        "key": "build_lumbermill_1",
        "name": "Лесопилка 1",
        "description": "Постройте/улучшите лесопилка до 1 уровня.",
        "building_key": "lumbermill",
        "threshold": 1,
        "bonus_pct": 0.5
    },
    {
        "key": "build_lumbermill_3",
        "name": "Лесопилка 3",
        "description": "Постройте/улучшите лесопилка до 3 уровня.",
        "building_key": "lumbermill",
        "threshold": 3,
        "bonus_pct": 0.5
    },
    {
        "key": "build_lumbermill_5",
        "name": "Лесопилка 5",
        "description": "Постройте/улучшите лесопилка до 5 уровня.",
        "building_key": "lumbermill",
        "threshold": 5,
        "bonus_pct": 0.5
    },
    {
        "key": "build_lumbermill_10",
        "name": "Лесопилка 10",
        "description": "Постройте/улучшите лесопилка до 10 уровня.",
        "building_key": "lumbermill",
        "threshold": 10,
        "bonus_pct": 0.5
    },
    {
        "key": "build_lumbermill_20",
        "name": "Лесопилка 20",
        "description": "Постройте/улучшите лесопилка до 20 уровня.",
        "building_key": "lumbermill",
        "threshold": 20,
        "bonus_pct": 0.5
    },
    {
        "key": "build_ore_mine_1",
        "name": "Рудная шахта 1",
        "description": "Постройте/улучшите рудная шахта до 1 уровня.",
        "building_key": "ore_mine",
        "threshold": 1,
        "bonus_pct": 0.5
    },
    {
        "key": "build_ore_mine_3",
        "name": "Рудная шахта 3",
        "description": "Постройте/улучшите рудная шахта до 3 уровня.",
        "building_key": "ore_mine",
        "threshold": 3,
        "bonus_pct": 0.5
    },
    {
        "key": "build_ore_mine_5",
        "name": "Рудная шахта 5",
        "description": "Постройте/улучшите рудная шахта до 5 уровня.",
        "building_key": "ore_mine",
        "threshold": 5,
        "bonus_pct": 0.5
    },
    {
        "key": "build_ore_mine_10",
        "name": "Рудная шахта 10",
        "description": "Постройте/улучшите рудная шахта до 10 уровня.",
        "building_key": "ore_mine",
        "threshold": 10,
        "bonus_pct": 0.5
    },
    {
        "key": "build_ore_mine_20",
        "name": "Рудная шахта 20",
        "description": "Постройте/улучшите рудная шахта до 20 уровня.",
        "building_key": "ore_mine",
        "threshold": 20,
        "bonus_pct": 0.5
    },
    {
        "key": "build_mill_1",
        "name": "Мельница 1",
        "description": "Постройте/улучшите мельница до 1 уровня.",
        "building_key": "mill",
        "threshold": 1,
        "bonus_pct": 0.5
    },
    {
        "key": "build_mill_3",
        "name": "Мельница 3",
        "description": "Постройте/улучшите мельница до 3 уровня.",
        "building_key": "mill",
        "threshold": 3,
        "bonus_pct": 0.5
    },
    {
        "key": "build_mill_5",
        "name": "Мельница 5",
        "description": "Постройте/улучшите мельница до 5 уровня.",
        "building_key": "mill",
        "threshold": 5,
        "bonus_pct": 0.5
    },
    {
        "key": "build_mill_10",
        "name": "Мельница 10",
        "description": "Постройте/улучшите мельница до 10 уровня.",
        "building_key": "mill",
        "threshold": 10,
        "bonus_pct": 0.5
    },
    {
        "key": "build_mill_20",
        "name": "Мельница 20",
        "description": "Постройте/улучшите мельница до 20 уровня.",
        "building_key": "mill",
        "threshold": 20,
        "bonus_pct": 0.5
    },
    {
        "key": "build_weavery_1",
        "name": "Ткацкая 1",
        "description": "Постройте/улучшите ткацкая до 1 уровня.",
        "building_key": "weavery",
        "threshold": 1,
        "bonus_pct": 0.5
    },
    {
        "key": "build_weavery_3",
        "name": "Ткацкая 3",
        "description": "Постройте/улучшите ткацкая до 3 уровня.",
        "building_key": "weavery",
        "threshold": 3,
        "bonus_pct": 0.5
    },
    {
        "key": "build_weavery_5",
        "name": "Ткацкая 5",
        "description": "Постройте/улучшите ткацкая до 5 уровня.",
        "building_key": "weavery",
        "threshold": 5,
        "bonus_pct": 0.5
    },
    {
        "key": "build_weavery_10",
        "name": "Ткацкая 10",
        "description": "Постройте/улучшите ткацкая до 10 уровня.",
        "building_key": "weavery",
        "threshold": 10,
        "bonus_pct": 0.5
    },
    {
        "key": "build_weavery_20",
        "name": "Ткацкая 20",
        "description": "Постройте/улучшите ткацкая до 20 уровня.",
        "building_key": "weavery",
        "threshold": 20,
        "bonus_pct": 0.5
    },
    {
        "key": "build_forge_1",
        "name": "Кузня 1",
        "description": "Постройте/улучшите кузня до 1 уровня.",
        "building_key": "forge",
        "threshold": 1,
        "bonus_pct": 0.5
    },
    {
        "key": "build_forge_3",
        "name": "Кузня 3",
        "description": "Постройте/улучшите кузня до 3 уровня.",
        "building_key": "forge",
        "threshold": 3,
        "bonus_pct": 0.5
    },
    {
        "key": "build_forge_5",
        "name": "Кузня 5",
        "description": "Постройте/улучшите кузня до 5 уровня.",
        "building_key": "forge",
        "threshold": 5,
        "bonus_pct": 0.5
    },
    {
        "key": "build_forge_10",
        "name": "Кузня 10",
        "description": "Постройте/улучшите кузня до 10 уровня.",
        "building_key": "forge",
        "threshold": 10,
        "bonus_pct": 0.5
    },
    {
        "key": "build_forge_20",
        "name": "Кузня 20",
        "description": "Постройте/улучшите кузня до 20 уровня.",
        "building_key": "forge",
        "threshold": 20,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_novice_1",
        "name": "Новички 1",
        "description": "Наймите 1 ед. типа новички.",
        "worker_key": "novice",
        "threshold": 1,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_novice_3",
        "name": "Новички 3",
        "description": "Наймите 3 ед. типа новички.",
        "worker_key": "novice",
        "threshold": 3,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_novice_5",
        "name": "Новички 5",
        "description": "Наймите 5 ед. типа новички.",
        "worker_key": "novice",
        "threshold": 5,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_novice_10",
        "name": "Новички 10",
        "description": "Наймите 10 ед. типа новички.",
        "worker_key": "novice",
        "threshold": 10,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_worker_1",
        "name": "Рабочие 1",
        "description": "Наймите 1 ед. типа рабочие.",
        "worker_key": "worker",
        "threshold": 1,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_worker_3",
        "name": "Рабочие 3",
        "description": "Наймите 3 ед. типа рабочие.",
        "worker_key": "worker",
        "threshold": 3,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_worker_5",
        "name": "Рабочие 5",
        "description": "Наймите 5 ед. типа рабочие.",
        "worker_key": "worker",
        "threshold": 5,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_worker_10",
        "name": "Рабочие 10",
        "description": "Наймите 10 ед. типа рабочие.",
        "worker_key": "worker",
        "threshold": 10,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_specialist_1",
        "name": "Специалисты 1",
        "description": "Наймите 1 ед. типа специалисты.",
        "worker_key": "specialist",
        "threshold": 1,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_specialist_3",
        "name": "Специалисты 3",
        "description": "Наймите 3 ед. типа специалисты.",
        "worker_key": "specialist",
        "threshold": 3,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_specialist_5",
        "name": "Специалисты 5",
        "description": "Наймите 5 ед. типа специалисты.",
        "worker_key": "specialist",
        "threshold": 5,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_specialist_10",
        "name": "Специалисты 10",
        "description": "Наймите 10 ед. типа специалисты.",
        "worker_key": "specialist",
        "threshold": 10,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_master_1",
        "name": "Мастера 1",
        "description": "Наймите 1 ед. типа мастера.",
        "worker_key": "master",
        "threshold": 1,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_master_3",
        "name": "Мастера 3",
        "description": "Наймите 3 ед. типа мастера.",
        "worker_key": "master",
        "threshold": 3,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_master_5",
        "name": "Мастера 5",
        "description": "Наймите 5 ед. типа мастера.",
        "worker_key": "master",
        "threshold": 5,
        "bonus_pct": 0.5
    },
    {
        "key": "worker_master_10",
        "name": "Мастера 10",
        "description": "Наймите 10 ед. типа мастера.",
        "worker_key": "master",
        "threshold": 10,
        "bonus_pct": 0.5
    }
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
    "dirham_price_base": 1500.0,
    "dirham_price_growth": 1.40,
    "dirham_daily_limit": 6,
    "free_chest_cooldown_seconds": 4 * 3600,
}
