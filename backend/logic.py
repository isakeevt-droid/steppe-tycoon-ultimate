
from __future__ import annotations

import json
import random
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .content import (
    ACHIEVEMENTS,
    BUILDINGS,
    CARAVAN_ROUTES,
    GUARDS,
    PROCESSING_RECIPES,
    RESOURCES,
    SETTINGS,
    TITLES,
    WORKERS,
    WORKER_UPGRADES,
)
from .economy import (
    calculate_building_output_per_second,
    calculate_building_price,
    calculate_dirham_buy_price,
    calculate_global_bonus_pct,
    calculate_market_price,
    calculate_mine_click_income,
    calculate_mine_upgrade_cost,
    calculate_rank_score,
    calculate_storage_capacity,
    calculate_storage_upgrade_cost,
    calculate_worker_bonus,
    calculate_worker_hire_cost,
    calculate_worker_salary_per_minute,
    determine_title_key,
    get_day_key,
    get_next_title,
    get_title_bonus_pct,
    now_utc,
)
from .models import (
    Caravan,
    Player,
    PlayerAchievement,
    PlayerBuilding,
    PlayerResource,
    PlayerTitle,
    PlayerWorker,
)


def _get_player(db: Session, telegram_id: str) -> Player:
    player = db.query(Player).filter(Player.telegram_id == telegram_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Игрок не найден")
    return player


def _building_map(player: Player) -> dict[str, PlayerBuilding]:
    return {item.building_key: item for item in player.buildings}


def _worker_map(player: Player) -> dict[str, PlayerWorker]:
    return {item.worker_key: item for item in player.workers}


def _resource_map(player: Player) -> dict[str, PlayerResource]:
    return {item.resource_key: item for item in player.resources}


def _achievement_map(player: Player) -> dict[str, PlayerAchievement]:
    return {item.achievement_key: item for item in player.achievements}


def _title_map(player: Player) -> dict[str, PlayerTitle]:
    return {item.title_key: item for item in player.titles}


def _get_or_create_resource(player: Player, key: str) -> PlayerResource:
    for item in player.resources:
        if item.resource_key == key:
            return item
    item = PlayerResource(player=player, resource_key=key, amount=0.0)
    player.resources.append(item)
    return item


def ensure_defaults(db: Session, player: Player) -> None:
    existing_buildings = _building_map(player)
    for key in BUILDINGS:
        if key not in existing_buildings:
            player.buildings.append(PlayerBuilding(player=player, building_key=key, level=0))
    existing_workers = _worker_map(player)
    for key in WORKERS:
        if key not in existing_workers:
            player.workers.append(PlayerWorker(player=player, worker_key=key, count=0))
    existing_resources = _resource_map(player)
    for key in RESOURCES:
        if key not in existing_resources:
            player.resources.append(PlayerResource(player=player, resource_key=key, amount=0.0))
    existing_achievements = _achievement_map(player)
    for item in ACHIEVEMENTS:
        if item["key"] not in existing_achievements:
            player.achievements.append(
                PlayerAchievement(player=player, achievement_key=item["key"], unlocked=False)
            )
    existing_titles = _title_map(player)
    for item in TITLES:
        if item["key"] not in existing_titles:
            player.titles.append(PlayerTitle(player=player, title_key=item["key"]))
    db.add(player)
    db.commit()
    db.refresh(player)


def get_or_create_player(db: Session, telegram_id: str, username: str | None = None) -> Player:
    player = db.query(Player).filter(Player.telegram_id == telegram_id).first()
    if not player:
        player = Player(
            telegram_id=telegram_id,
            username=(username or "Игрок")[:64],
            gold=SETTINGS["start_gold"],
            free_chest_ready_at=now_utc(),
        )
        db.add(player)
        db.commit()
        db.refresh(player)
    elif username:
        player.username = username[:64]
    ensure_defaults(db, player)
    tick_player(db, player)
    return player


def _storage_used(player: Player) -> float:
    return sum(max(0.0, item.amount) for item in player.resources)


def _worker_counts(player: Player) -> dict[str, int]:
    return {item.worker_key: item.count for item in player.workers}


def _building_levels(player: Player) -> dict[str, int]:
    return {item.building_key: item.level for item in player.buildings}


def _achievement_bonus_pct(player: Player) -> float:
    unlocked = {a.achievement_key for a in player.achievements if a.unlocked}
    total = 0.0
    for item in ACHIEVEMENTS:
        if item["key"] in unlocked:
            total += item["bonus_pct"]
    return min(total, 100.0)


def _market_seed() -> int:
    now = now_utc()
    return int(now.timestamp() // 600)


def tick_player(db: Session, player: Player) -> None:
    ensure_defaults(db, player)
    now = now_utc()
    if player.dirham_day_key != get_day_key(now):
        player.dirham_day_key = get_day_key(now)
        player.dirhams_bought_today = 0

    elapsed = max(0.0, (now - player.last_tick_at).total_seconds())
    if elapsed <= 0:
        _update_titles_and_achievements(db, player)
        db.commit()
        db.refresh(player)
        return

    worker_counts = _worker_counts(player)
    worker_bonus = calculate_worker_bonus(worker_counts)
    salary_per_minute = calculate_worker_salary_per_minute(worker_counts)
    salary_due = salary_per_minute * (elapsed / 60.0)
    payroll_ok = player.gold >= salary_due
    if salary_due > 0:
        paid = min(player.gold, salary_due)
        player.gold -= paid
        player.total_gold_spent += paid

    achievement_bonus = _achievement_bonus_pct(player)
    title_bonus = get_title_bonus_pct(player.title_key)
    global_bonus = calculate_global_bonus_pct(achievement_bonus, title_bonus)
    levels = _building_levels(player)
    resources = _resource_map(player)

    capacity = calculate_storage_capacity(player.storage_level)
    storage_used = _storage_used(player)

    for key, level in levels.items():
        if level <= 0:
            continue
        item = BUILDINGS[key]
        if item["category"] != "production":
            continue
        if storage_used >= capacity:
            break
        produced = calculate_building_output_per_second(key, level, worker_bonus, global_bonus, payroll_ok) * elapsed
        produced = round(max(produced, 0.0), 4)
        if produced <= 0:
            continue
        free_space = capacity - storage_used
        actual = min(produced, max(0.0, free_space))
        if actual <= 0:
            continue
        resources[item["resource_key"]].amount += actual
        storage_used += actual
        player.total_resources_produced += actual

    player.last_tick_at = now
    _update_titles_and_achievements(db, player)
    db.add(player)
    db.commit()
    db.refresh(player)


def _update_titles_and_achievements(db: Session, player: Player) -> None:
    score = calculate_rank_score(
        player,
        total_building_levels=sum(x.level for x in player.buildings),
        worker_count=sum(x.count for x in player.workers),
    )
    new_title_key = determine_title_key(score)
    player.title_key = new_title_key

    tmap = _title_map(player)
    for item in TITLES:
        if score >= item["score"]:
            if tmap[item["key"]].unlocked_at is None:
                tmap[item["key"]].unlocked_at = now_utc()
                player.dirhams += 2 if item["score"] < 50000 else 3

    bmap = _building_levels(player)
    wmap = _worker_counts(player)
    amap = _achievement_map(player)

    for item in ACHIEVEMENTS:
        ach = amap[item["key"]]
        if ach.unlocked:
            continue
        unlocked = False
        if "stat" in item:
            unlocked = getattr(player, item["stat"]) >= item["threshold"]
        elif "building_key" in item:
            unlocked = bmap.get(item["building_key"], 0) >= item["threshold"]
        elif "worker_key" in item:
            unlocked = wmap.get(item["worker_key"], 0) >= item["threshold"]
        if unlocked:
            ach.unlocked = True
            ach.unlocked_at = now_utc()
            player.dirhams += 1 if item["bonus_pct"] <= 0.5 else 2


def make_state(db: Session, telegram_id: str) -> dict:
    player = db.query(Player).filter(Player.telegram_id == telegram_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Игрок не найден")

    tick_player(db, player)
    return _serialize_state(db, player)
    tick_player(db, player)
    return _serialize_state(db, player)


def _serialize_state(db: Session, player: Player) -> dict:
    achievement_bonus = _achievement_bonus_pct(player)
    title_bonus = get_title_bonus_pct(player.title_key)
    total_bonus = achievement_bonus + title_bonus
    market_seed = _market_seed()

    title_meta = next((t for t in TITLES if t["key"] == player.title_key), TITLES[0])
    next_title = get_next_title(player.title_key)
    rank_score = calculate_rank_score(
        player,
        total_building_levels=sum(x.level for x in player.buildings),
        worker_count=sum(x.count for x in player.workers),
    )
    capacity = calculate_storage_capacity(player.storage_level)
    used = _storage_used(player)
    market_prices = {k: calculate_market_price(k, market_seed) for k in RESOURCES}

    buildings = []
    for pb in sorted(player.buildings, key=lambda x: x.building_key):
        cfg = BUILDINGS[pb.building_key]
        buildings.append({
            "key": pb.building_key,
            "name": cfg["name"],
            "level": pb.level,
            "price": round(calculate_building_price(pb.building_key, pb.level), 2),
            "description": cfg["description"],
            "category": cfg["category"],
            "resource_key": cfg.get("resource_key"),
            "input_key": cfg.get("input_key"),
            "output_key": cfg.get("output_key"),
        })

    workers = []
    for pw in sorted(player.workers, key=lambda x: x.worker_key):
        cfg = WORKERS[pw.worker_key]
        workers.append({
            "key": pw.worker_key,
            "name": cfg["name"],
            "count": pw.count,
            "hire_cost": cfg["hire_cost"],
            "salary": cfg["salary_per_minute"],
            "efficiency_bonus_pct": round(cfg["efficiency_bonus"] * 100, 1),
            "description": cfg["description"],
        })

    resources = []
    for pr in sorted(player.resources, key=lambda x: x.resource_key):
        cfg = RESOURCES[pr.resource_key]
        resources.append({
            "key": pr.resource_key,
            "name": cfg["name"],
            "amount": round(pr.amount, 2),
            "kind": cfg["kind"],
            "market_price": market_prices[pr.resource_key],
        })

    achievements = []
    unlocked_set = {a.achievement_key for a in player.achievements if a.unlocked}
    for item in ACHIEVEMENTS:
        progress = 0.0
        current = 0.0
        if "stat" in item:
            current = float(getattr(player, item["stat"]))
            progress = min(100.0, (current / item["threshold"]) * 100.0)
        elif "building_key" in item:
            current = next((x.level for x in player.buildings if x.building_key == item["building_key"]), 0)
            progress = min(100.0, (current / item["threshold"]) * 100.0)
        elif "worker_key" in item:
            current = next((x.count for x in player.workers if x.worker_key == item["worker_key"]), 0)
            progress = min(100.0, (current / item["threshold"]) * 100.0)
        achievements.append({
            "key": item["key"],
            "name": item["name"],
            "description": item["description"],
            "threshold": item["threshold"],
            "current": round(current, 2),
            "progress_pct": round(progress, 1),
            "bonus_pct": item["bonus_pct"],
            "unlocked": item["key"] in unlocked_set,
        })

    title_unlocked = {t.title_key for t in player.titles if t.unlocked_at is not None}
    titles = [{
        "key": item["key"],
        "name": item["name"],
        "score": item["score"],
        "bonus_pct": item["bonus_pct"],
        "unlocked": item["key"] in title_unlocked,
        "current": round(rank_score, 2),
        "progress_pct": min(100.0, round((rank_score / item["score"]) * 100.0, 1)),
    } for item in TITLES]

    active_caravans = []
    for caravan in player.caravans[:15]:
        cargo = json.loads(caravan.cargo_json or "{}")
        remaining = max(0, int((caravan.ends_at - now_utc()).total_seconds()))
        route_meta = CARAVAN_ROUTES.get(caravan.route_key, {})
        active_caravans.append({
            "id": caravan.id,
            "route_key": caravan.route_key,
            "route_name": route_meta.get("name", caravan.route_key),
            "guard_level": caravan.guard_level,
            "guard_name": GUARDS.get(caravan.guard_level, {}).get("name", caravan.guard_level),
            "cargo": cargo,
            "cargo_value": caravan.cargo_value,
            "expected_profit": caravan.expected_profit,
            "risk_percent": caravan.risk_percent,
            "status": caravan.status,
            "resolved": caravan.resolved,
            "success": caravan.success,
            "result_gold": caravan.result_gold,
            "result_dirhams": caravan.result_dirhams,
            "event_text": caravan.event_text,
            "remaining_seconds": remaining,
        })

    leaderboard_query = db.query(Player).order_by(Player.total_gold_earned.desc()).limit(20).all()
    leaderboard = []
    for idx, p in enumerate(leaderboard_query, start=1):
        tmeta = next((t for t in TITLES if t["key"] == p.title_key), TITLES[0])
        leaderboard.append({
            "rank": idx,
            "username": p.username,
            "gold_earned": round(p.total_gold_earned, 2),
            "title_name": tmeta["name"],
        })

    tooltips = {
        "gold": "Основная валюта. Нужна для зданий, найма и развития.",
        "dirhams": "Редкая валюта. Используется для охраны караванов и улучшения работников.",
        "storage": "Если склад заполнен, производство останавливается.",
        "caravan": "Караваны дают больше прибыли, но имеют риск потери груза.",
        "mine": "Шахта даёт небольшой дополнительный доход кликами.",
    }

    return {
        "player": {
            "telegram_id": player.telegram_id,
            "username": player.username,
            "gold": round(player.gold, 2),
            "dirhams": player.dirhams,
            "title_key": player.title_key,
            "title_name": title_meta["name"],
            "rank_score": round(rank_score, 2),
            "next_title": next_title,
            "storage_level": player.storage_level,
            "storage_capacity": round(capacity, 2),
            "storage_used": round(used, 2),
            "total_bonus_pct": round(total_bonus, 2),
            "mine_level": player.manual_mine_level,
            "mine_upgrade_cost": round(calculate_mine_upgrade_cost(player.manual_mine_level), 2),
            "dirham_price": round(calculate_dirham_buy_price(player.dirhams_bought_today), 2),
            "dirham_daily_limit": SETTINGS["dirham_daily_limit"],
            "dirhams_bought_today": player.dirhams_bought_today,
            "storage_upgrade_cost": round(calculate_storage_upgrade_cost(player.storage_level), 2),
            "total_gold_earned": round(player.total_gold_earned, 2),
            "total_gold_spent": round(player.total_gold_spent, 2),
            "total_resources_produced": round(player.total_resources_produced, 2),
            "total_resources_processed": round(player.total_resources_processed, 2),
            "total_caravans_sent": player.total_caravans_sent,
            "total_caravans_success": player.total_caravans_success,
            "total_clicks": player.total_clicks,
        },
        "buildings": buildings,
        "workers": workers,
        "resources": resources,
        "caravan_routes": [{"key": k, **v} for k, v in CARAVAN_ROUTES.items()],
        "active_caravans": active_caravans,
        "achievements": achievements,
        "titles": titles,
        "leaderboard": leaderboard,
        "market_prices": market_prices,
        "server_time": now_utc().isoformat(),
        "tooltips": tooltips,
    }


def buy_building(db: Session, telegram_id: str, building_key: str) -> dict:
    if building_key not in BUILDINGS:
        raise HTTPException(status_code=400, detail="Неизвестное здание")
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    pb = next(x for x in player.buildings if x.building_key == building_key)
    price = calculate_building_price(building_key, pb.level)
    if player.gold < price:
        raise HTTPException(status_code=400, detail="Недостаточно золота")
    player.gold -= price
    player.total_gold_spent += price
    pb.level += 1
    db.commit()
    return _serialize_state(db, player)


def hire_worker(db: Session, telegram_id: str, worker_key: str) -> dict:
    if worker_key not in WORKERS:
        raise HTTPException(status_code=400, detail="Неизвестный тип работника")
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    price = calculate_worker_hire_cost(worker_key)
    if player.gold < price:
        raise HTTPException(status_code=400, detail="Недостаточно золота")
    player.gold -= price
    player.total_gold_spent += price
    pw = next(x for x in player.workers if x.worker_key == worker_key)
    pw.count += 1
    db.commit()
    return _serialize_state(db, player)


def upgrade_worker(db: Session, telegram_id: str, upgrade_key: str) -> dict:
    if upgrade_key not in WORKER_UPGRADES:
        raise HTTPException(status_code=400, detail="Неизвестное улучшение")
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    cfg = WORKER_UPGRADES[upgrade_key]
    src = next(x for x in player.workers if x.worker_key == cfg["from"])
    dst = next(x for x in player.workers if x.worker_key == cfg["to"])
    if src.count < 1:
        raise HTTPException(status_code=400, detail="Нет работника для улучшения")
    if player.dirhams < cfg["cost_dirhams"]:
        raise HTTPException(status_code=400, detail="Недостаточно дирхамов")
    player.dirhams -= cfg["cost_dirhams"]
    player.total_dirhams_spent += cfg["cost_dirhams"]
    src.count -= 1
    dst.count += 1
    db.commit()
    return _serialize_state(db, player)


def process_resources(db: Session, telegram_id: str, recipe_key: str, amount: float) -> dict:
    recipe_map = {
        "mill": PROCESSING_RECIPES["mill"],
        "weavery": PROCESSING_RECIPES["weavery"],
        "forge": PROCESSING_RECIPES["forge"],
        "planks": PROCESSING_RECIPES["sawmill_process"],
    }
    if recipe_key not in recipe_map:
        raise HTTPException(status_code=400, detail="Неизвестный рецепт")
    player = _get_player(db, telegram_id)
    tick_player(db, player)

    recipe = recipe_map[recipe_key]
    in_res = _get_or_create_resource(player, recipe["input_key"])
    out_res = _get_or_create_resource(player, recipe["output_key"])
    if in_res.amount < amount:
        raise HTTPException(status_code=400, detail="Недостаточно сырья")
    capacity = calculate_storage_capacity(player.storage_level)
    free_space = capacity - _storage_used(player)
    produced = amount
    if free_space + amount < produced:
        raise HTTPException(status_code=400, detail="Недостаточно места на складе")
    in_res.amount -= amount
    out_res.amount += produced
    player.total_resources_processed += produced * recipe["multiplier"]
    db.commit()
    return _serialize_state(db, player)


def sell_resource(db: Session, telegram_id: str, resource_key: str, amount: float) -> dict:
    if resource_key not in RESOURCES:
        raise HTTPException(status_code=400, detail="Неизвестный ресурс")
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    res = _get_or_create_resource(player, resource_key)
    if res.amount < amount:
        raise HTTPException(status_code=400, detail="Недостаточно ресурса")
    market_price = calculate_market_price(resource_key, _market_seed())
    total = amount * market_price
    res.amount -= amount
    player.gold += total
    player.total_gold_earned += total
    db.commit()
    return _serialize_state(db, player)


def buy_dirham(db: Session, telegram_id: str) -> dict:
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    if player.dirhams_bought_today >= SETTINGS["dirham_daily_limit"]:
        raise HTTPException(status_code=400, detail="Дневной лимит достигнут")
    price = calculate_dirham_buy_price(player.dirhams_bought_today)
    if player.gold < price:
        raise HTTPException(status_code=400, detail="Недостаточно золота")
    player.gold -= price
    player.total_gold_spent += price
    player.dirhams += 1
    player.total_dirhams_bought += 1
    player.dirhams_bought_today += 1
    db.commit()
    return _serialize_state(db, player)


def storage_upgrade(db: Session, telegram_id: str) -> dict:
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    price = calculate_storage_upgrade_cost(player.storage_level)
    if player.gold < price:
        raise HTTPException(status_code=400, detail="Недостаточно золота")
    player.gold -= price
    player.total_gold_spent += price
    player.storage_level += 1
    db.commit()
    return _serialize_state(db, player)


def mine_click(db: Session, telegram_id: str) -> dict:
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    income = calculate_mine_click_income(
        player.manual_mine_level,
        _achievement_bonus_pct(player),
        get_title_bonus_pct(player.title_key),
    )
    player.gold += income
    player.total_gold_earned += income
    player.total_clicks += 1
    db.commit()
    return _serialize_state(db, player)


def mine_upgrade(db: Session, telegram_id: str) -> dict:
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    price = calculate_mine_upgrade_cost(player.manual_mine_level)
    if player.gold < price:
        raise HTTPException(status_code=400, detail="Недостаточно золота")
    player.gold -= price
    player.total_gold_spent += price
    player.manual_mine_level += 1
    db.commit()
    return _serialize_state(db, player)


def send_caravan(
    db: Session,
    telegram_id: str,
    route_key: str,
    guard_level: str,
    resource_key: str,
    amount: float,
) -> dict:
    if route_key not in CARAVAN_ROUTES:
        raise HTTPException(status_code=400, detail="Неизвестный маршрут")
    if guard_level not in GUARDS:
        raise HTTPException(status_code=400, detail="Неизвестный уровень охраны")
    if resource_key not in RESOURCES:
        raise HTTPException(status_code=400, detail="Неизвестный ресурс")
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    resource = _get_or_create_resource(player, resource_key)
    if resource.amount < amount:
        raise HTTPException(status_code=400, detail="Недостаточно ресурса")
    guard = GUARDS[guard_level]
    if player.dirhams < guard["cost_dirhams"]:
        raise HTTPException(status_code=400, detail="Недостаточно дирхамов")
    route = CARAVAN_ROUTES[route_key]
    cargo_value = amount * calculate_market_price(resource_key, _market_seed())
    risk = max(0.0, route["risk_percent"] - guard["risk_reduction"])
    expected_profit = cargo_value * (1 + route["profit_bonus"])

    duration_seconds = route["duration_seconds"]
    if route.get("bonus_type") == "time_reduction":
        duration_seconds = max(60, int(duration_seconds * (1 - route["bonus_value"])))
    resource.amount -= amount
    player.dirhams -= guard["cost_dirhams"]
    player.total_dirhams_spent += guard["cost_dirhams"]
    player.total_caravans_sent += 1

    caravan = Caravan(
        player=player,
        route_key=route_key,
        guard_level=guard_level,
        cargo_json=json.dumps({resource_key: amount}, ensure_ascii=False),
        cargo_value=cargo_value,
        expected_profit=expected_profit,
        risk_percent=risk,
        ends_at=now_utc() + timedelta(seconds=duration_seconds),
        status="traveling",
    )
    db.add(caravan)
    db.commit()
    return _serialize_state(db, player)


def claim_caravan(db: Session, telegram_id: str, caravan_id: int) -> dict:
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    caravan = db.query(Caravan).filter(Caravan.id == caravan_id, Caravan.player_id == player.id).first()
    if not caravan:
        raise HTTPException(status_code=404, detail="Караван не найден")
    if caravan.resolved:
        raise HTTPException(status_code=400, detail="Караван уже завершён")
    if caravan.ends_at > now_utc():
        raise HTTPException(status_code=400, detail="Караван ещё в пути")

    success = random.random() >= (caravan.risk_percent / 100.0)
    route = CARAVAN_ROUTES[caravan.route_key]
    caravan.resolved = True
    caravan.success = success
    caravan.status = "success" if success else "failed"
    caravan.event_text = None

    if success:
        cargo = json.loads(caravan.cargo_json or "{}")
        resource_key = next(iter(cargo.keys()), None)
        resource_kind = RESOURCES.get(resource_key, {}).get("kind") if resource_key else None

        gold = round(caravan.expected_profit, 2)

        if route.get("bonus_type") == "raw_bonus" and resource_kind == "raw":
            gold *= (1 + route["bonus_value"])
        elif route.get("bonus_type") == "processed_bonus" and resource_kind == "processed":
            gold *= (1 + route["bonus_value"])
        elif route.get("bonus_type") == "gold_bonus":
            gold *= (1 + route["bonus_value"])

        if route.get("bonus_type") == "success_chance":
            success_roll_boost = route["bonus_value"]
        else:
            success_roll_boost = 0.0

        roll = random.random()
        if roll < 0.02:
            gold *= 2
            caravan.event_text = "Двойная прибыль"
        elif roll < 0.10:
            gold *= 1.2
            caravan.event_text = "Удачная торговля"
        elif roll < 0.14:
            guard = caravan.guard_level
            if guard == "none":
                gold *= 0.75
            elif guard == "basic":
                gold *= 0.85
            elif guard == "experienced":
                gold *= 0.95
            elif guard == "elite":
                gold *= 1.0
            caravan.event_text = "Нападение кочевников"

        gold = round(gold, 2)
        player.gold += gold
        player.total_gold_earned += gold
        player.total_caravans_success += 1
        player.total_caravan_profit += gold
        caravan.result_gold = gold

        if route.get("bonus_type") == "dirham_chance" and random.random() < route["bonus_value"]:
            player.dirhams += 1
            caravan.result_dirhams += 1
        if route.get("bonus_type") == "dirham_chance" and random.random() < 0.03:
            player.dirhams += 2
            caravan.result_dirhams += 2
    else:
        caravan.result_gold = 0.0

    db.commit()
    return _serialize_state(db, player)
def open_chest(db: Session, telegram_id: str) -> dict:
    player = _get_player(db, telegram_id)
    tick_player(db, player)

    now = now_utc()

    if player.free_chest_ready_at > now:
        raise HTTPException(status_code=400, detail="Сундук ещё не готов")

    reward_gold = random.randint(40, 90)
    reward_dirhams = 1 if random.random() < 0.35 else 0

    player.gold += reward_gold
    player.total_gold_earned += reward_gold

    if reward_dirhams > 0:
        player.dirhams += reward_dirhams

    cooldown = SETTINGS["free_chest_cooldown_seconds"]
    player.free_chest_ready_at = now + timedelta(seconds=cooldown)

    db.commit()
    return _serialize_state(db, player)