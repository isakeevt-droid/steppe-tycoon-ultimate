from __future__ import annotations

import json
import random
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .content import ACHIEVEMENTS, BUILDINGS, CARAVAN_ROUTES, GUARDS, PROCESSING_RECIPES, RESOURCES, SETTINGS, TITLES, WORKERS, WORKER_UPGRADES
from .economy import (
    calculate_auto_activation_cost,
    calculate_building_output_per_second,
    calculate_building_price,
    calculate_dirham_buy_price,
    calculate_global_bonus_pct,
    calculate_market_price,
    calculate_mine_click_income,
    calculate_mine_upgrade_cost,
    calculate_pickaxe_upgrade_cost,
    calculate_processing_output_per_second,
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
from .models import Caravan, Player, PlayerAchievement, PlayerBuilding, PlayerResource, PlayerTitle, PlayerWorker


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
            player.buildings.append(PlayerBuilding(player=player, building_key=key, level=0, auto_mode="off"))
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
            player.achievements.append(PlayerAchievement(player=player, achievement_key=item["key"], unlocked=False))
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
        player = Player(telegram_id=telegram_id, username=(username or "Игрок")[:64], gold=SETTINGS["start_gold"], free_chest_ready_at=now_utc())
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
    return int(now_utc().timestamp() // 600)


def _auto_active(pb: PlayerBuilding, now=None) -> bool:
    now = now or now_utc()
    return pb.auto_until is not None and pb.auto_until > now and pb.auto_mode != "off"


def tick_player(db: Session, player: Player) -> None:
    ensure_defaults(db, player)
    now = now_utc()
    if player.dirham_day_key != get_day_key(now):
        player.dirham_day_key = get_day_key(now)
        player.dirhams_bought_today = 0

    elapsed = max(0.0, (now - player.last_tick_at).total_seconds())
    if elapsed <= 0:
        _update_titles_and_achievements(player)
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
    resources = _resource_map(player)
    capacity = calculate_storage_capacity(player.storage_level)
    storage_used = _storage_used(player)
    market_seed = _market_seed()

    # passive raw production
    for pb in player.buildings:
        cfg = BUILDINGS[pb.building_key]
        if pb.level <= 0 or cfg["category"] != "production":
            continue
        if storage_used >= capacity:
            break
        produced = calculate_building_output_per_second(pb.building_key, pb.level, worker_bonus, global_bonus, payroll_ok) * elapsed
        produced = max(0.0, round(produced, 4))
        if produced <= 0:
            continue
        actual = min(produced, max(0.0, capacity - storage_used))
        if actual <= 0:
            continue
        resources[cfg["resource_key"]].amount += actual
        storage_used += actual
        player.total_resources_produced += actual

    # passive processing: processing buildings always convert while there is input and free space
    for pb in player.buildings:
        cfg = BUILDINGS[pb.building_key]
        if pb.level <= 0 or cfg["category"] != "processing":
            continue
        per_sec = calculate_processing_output_per_second(pb.level, cfg.get("batch_size", 10), worker_bonus, global_bonus, payroll_ok)
        amount = round(max(0.0, per_sec * elapsed), 4)
        if amount <= 0:
            continue
        input_res = resources[cfg["input_key"]]
        output_res = resources[cfg["output_key"]]
        amount = min(amount, input_res.amount)
        free_space = max(0.0, capacity - storage_used)
        amount = min(amount, free_space)
        if amount <= 0:
            continue
        input_res.amount -= amount
        output_res.amount += amount
        player.total_resources_processed += amount

    # timed automation: production buildings auto-sell at current production speed
    for pb in player.buildings:
        cfg = BUILDINGS[pb.building_key]
        if pb.level <= 0 or cfg["category"] != "production" or not _auto_active(pb, now):
            continue
        active_elapsed = min(elapsed, max(0.0, (pb.auto_until - player.last_tick_at).total_seconds()))
        if active_elapsed <= 0:
            continue
        res = resources[cfg["resource_key"]]
        if res.amount <= 0:
            continue

        auto_sell_per_sec = calculate_building_output_per_second(
            pb.building_key,
            pb.level,
            worker_bonus,
            global_bonus,
            payroll_ok,
        )
        sell_amount = min(res.amount, round(auto_sell_per_sec * active_elapsed, 4))
        if sell_amount <= 0:
            continue
        market_price = calculate_market_price(cfg["resource_key"], market_seed)
        total = round(sell_amount * market_price, 2)
        res.amount -= sell_amount
        player.gold += total
        player.total_gold_earned += total

    player.last_tick_at = now
    _update_titles_and_achievements(player)
    db.add(player)
    db.commit()
    db.refresh(player)


def _update_titles_and_achievements(player: Player) -> None:
    score = calculate_rank_score(player, total_building_levels=sum(x.level for x in player.buildings), worker_count=sum(x.count for x in player.workers))
    player.title_key = determine_title_key(score)
    tmap = _title_map(player)
    for item in TITLES:
        if score >= item["score"] and tmap[item["key"]].unlocked_at is None:
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


def _build_caravan_preview() -> list[dict]:
    return [{"key": key, **value} for key, value in CARAVAN_ROUTES.items()]


def make_state(db: Session, telegram_id: str) -> dict:
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    return _serialize_state(db, player)


def _serialize_state(db: Session, player: Player) -> dict:
    achievement_bonus = _achievement_bonus_pct(player)
    title_bonus = get_title_bonus_pct(player.title_key)
    total_bonus = achievement_bonus + title_bonus
    market_seed = _market_seed()
    title_meta = next((t for t in TITLES if t["key"] == player.title_key), TITLES[0])
    next_title = get_next_title(player.title_key)
    rank_score = calculate_rank_score(player, total_building_levels=sum(x.level for x in player.buildings), worker_count=sum(x.count for x in player.workers))
    capacity = calculate_storage_capacity(player.storage_level)
    used = _storage_used(player)
    market_prices = {k: calculate_market_price(k, market_seed) for k in RESOURCES}
    worker_counts = _worker_counts(player)
    worker_bonus = calculate_worker_bonus(worker_counts)
    global_bonus = calculate_global_bonus_pct(achievement_bonus, title_bonus)
    resources_map = _resource_map(player)
    now = now_utc()
    base_tap, avg_tap, crit_chance, crit_mult = calculate_mine_click_income(player.manual_mine_level, player.mine_pickaxe_level, achievement_bonus, title_bonus)

    buildings = []
    notifications = []
    for pb in sorted(player.buildings, key=lambda x: x.building_key):
        cfg = BUILDINGS[pb.building_key]
        price = round(calculate_building_price(pb.building_key, pb.level), 2)
        auto_active = _auto_active(pb, now)
        auto_seconds = max(0, int((pb.auto_until - now).total_seconds())) if pb.auto_until else 0
        auto_kind = "sell" if cfg["category"] == "production" else "process"
        if pb.auto_until is not None and pb.auto_until <= now and pb.auto_mode != "off":
            notifications.append(f"{cfg['name']}: авто-{ 'продажа' if auto_kind == 'sell' else 'переработка' } остановлена.")
            pb.auto_mode = "off"
            pb.auto_until = None
            auto_seconds = 0
            auto_active = False
        record = {
            "key": pb.building_key,
            "name": cfg["name"],
            "level": pb.level,
            "price": price,
            "description": cfg["description"],
            "category": cfg["category"],
            "resource_key": cfg.get("resource_key"),
            "input_key": cfg.get("input_key"),
            "output_key": cfg.get("output_key"),
            "auto_kind": auto_kind,
            "auto_active": auto_active,
            "auto_seconds": auto_seconds,
            "auto_cost_dirhams": calculate_auto_activation_cost(pb.level),
            "auto_hours": SETTINGS["auto_hours"],
        }
        if cfg["category"] == "production":
            now_per_sec = calculate_building_output_per_second(pb.building_key, pb.level, worker_bonus, global_bonus, True)
            next_per_sec = calculate_building_output_per_second(pb.building_key, pb.level + 1, worker_bonus, global_bonus, True)
            record.update({
                "current_per_min": round(now_per_sec * 60, 2),
                "next_per_min": round(next_per_sec * 60, 2),
                "income_now_per_min": round(now_per_sec * 60 * market_prices[cfg["resource_key"]], 2),
                "income_next_per_min": round(next_per_sec * 60 * market_prices[cfg["resource_key"]], 2),
                "resource_amount": round(resources_map[cfg["resource_key"]].amount, 2),
            })
        else:
            per_sec = calculate_processing_output_per_second(pb.level, cfg.get("batch_size", 10), worker_bonus, global_bonus, True)
            next_per_sec = calculate_processing_output_per_second(pb.level + 1, cfg.get("batch_size", 10), worker_bonus, global_bonus, True)
            record.update({
                "input_amount": round(resources_map[cfg["input_key"]].amount, 2),
                "output_amount": round(resources_map[cfg["output_key"]].amount, 2),
                "current_per_min": round(per_sec * 60, 2),
                "next_per_min": round(next_per_sec * 60, 2),
            })
        buildings.append(record)

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
        current = 0.0
        if "stat" in item:
            current = float(getattr(player, item["stat"]))
        elif "building_key" in item:
            current = next((x.level for x in player.buildings if x.building_key == item["building_key"]), 0)
        elif "worker_key" in item:
            current = next((x.count for x in player.workers if x.worker_key == item["worker_key"]), 0)
        achievements.append({
            "key": item["key"],
            "name": item["name"],
            "description": item["description"],
            "threshold": item["threshold"],
            "current": round(current, 2),
            "bonus_pct": item["bonus_pct"],
            "unlocked": item["key"] in unlocked_set,
        })

    caravans = []
    for caravan in player.caravans[:50]:
        cargo = json.loads(caravan.cargo_json or "{}")
        remaining = max(0, int((caravan.ends_at - now).total_seconds()))
        route_meta = CARAVAN_ROUTES.get(caravan.route_key, {})
        caravans.append({
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
    leaderboard = [{"rank": i, "username": p.username, "gold_earned": round(p.total_gold_earned, 2), "title_name": next((t for t in TITLES if t['key']==p.title_key), TITLES[0])["name"]} for i, p in enumerate(leaderboard_query, start=1)]

    completed = [x for x in achievements if x["unlocked"]]
    active = [x for x in achievements if not x["unlocked"]][:6]

    db.commit()
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
            "pickaxe_level": player.mine_pickaxe_level,
            "mine_upgrade_cost": round(calculate_mine_upgrade_cost(player.manual_mine_level), 2),
            "pickaxe_upgrade_cost": round(calculate_pickaxe_upgrade_cost(player.mine_pickaxe_level), 2),
            "mine_base_tap": base_tap,
            "mine_income": avg_tap,
            "mine_crit_chance": crit_chance,
            "mine_crit_multiplier": crit_mult,
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
            "active_caravans_count": sum(1 for c in player.caravans if not c.resolved),
            "max_active_caravans": SETTINGS["max_active_caravans"],
            "chest_ready": player.free_chest_ready_at <= now,
            "chest_seconds": max(0, int((player.free_chest_ready_at - now).total_seconds())),
        },
        "buildings": buildings,
        "resources": resources,
        "workers": [{"key": pw.worker_key, "name": WORKERS[pw.worker_key]["name"], "count": pw.count, "hire_cost": WORKERS[pw.worker_key]["hire_cost"], "salary": WORKERS[pw.worker_key]["salary_per_minute"], "efficiency_bonus_pct": round(WORKERS[pw.worker_key]["efficiency_bonus"]*100,1), "description": WORKERS[pw.worker_key]["description"]} for pw in sorted(player.workers, key=lambda x: x.worker_key)],
        "caravan_routes": _build_caravan_preview(),
        "active_caravans": caravans,
        "achievements": achievements,
        "active_achievements": active,
        "completed_achievements": completed,
        "leaderboard": leaderboard,
        "notifications": notifications,
        "server_time": now.isoformat(),
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
    next(x for x in player.workers if x.worker_key == worker_key).count += 1
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
    if recipe_key not in PROCESSING_RECIPES:
        raise HTTPException(status_code=400, detail="Неизвестный рецепт")
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    recipe = PROCESSING_RECIPES[recipe_key]
    building = next(x for x in player.buildings if x.building_key == recipe["building_key"])
    if building.level <= 0:
        raise HTTPException(status_code=400, detail="Сначала построй перерабатывающее здание")
    in_res = _get_or_create_resource(player, recipe["input_key"])
    out_res = _get_or_create_resource(player, recipe["output_key"])
    if in_res.amount < amount:
        raise HTTPException(status_code=400, detail="Недостаточно сырья")
    free_space = calculate_storage_capacity(player.storage_level) - _storage_used(player)
    if free_space < amount:
        raise HTTPException(status_code=400, detail="Недостаточно места на складе")
    in_res.amount -= amount
    out_res.amount += amount
    player.total_resources_processed += amount
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
    total = amount * calculate_market_price(resource_key, _market_seed())
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
    base_tap, _, crit_chance, crit_mult = calculate_mine_click_income(player.manual_mine_level, player.mine_pickaxe_level, _achievement_bonus_pct(player), get_title_bonus_pct(player.title_key))
    is_crit = random.random() < (crit_chance / 100.0)
    income = round(base_tap * (crit_mult if is_crit else 1.0), 2)
    player.gold += income
    player.total_gold_earned += income
    player.total_clicks += 1
    db.commit()
    state = _serialize_state(db, player)
    state["mine_click"] = {"income": income, "critical": is_crit}
    return state


def mine_upgrade(db: Session, telegram_id: str, upgrade_type: str = "mine") -> dict:
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    if upgrade_type == "pickaxe":
        price = calculate_pickaxe_upgrade_cost(player.mine_pickaxe_level)
        if player.gold < price:
            raise HTTPException(status_code=400, detail="Недостаточно золота")
        player.gold -= price
        player.total_gold_spent += price
        player.mine_pickaxe_level += 1
    else:
        price = calculate_mine_upgrade_cost(player.manual_mine_level)
        if player.gold < price:
            raise HTTPException(status_code=400, detail="Недостаточно золота")
        player.gold -= price
        player.total_gold_spent += price
        player.manual_mine_level += 1
    db.commit()
    return _serialize_state(db, player)


def toggle_building_automation(db: Session, telegram_id: str, building_key: str) -> dict:
    if building_key not in BUILDINGS:
        raise HTTPException(status_code=400, detail="Неизвестное здание")
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    pb = next(x for x in player.buildings if x.building_key == building_key)
    if pb.level <= 0:
        raise HTTPException(status_code=400, detail="Сначала построй это здание")
    if _auto_active(pb):
        pb.auto_mode = "off"
        pb.auto_until = None
    else:
        cost = calculate_auto_activation_cost(pb.level)
        if player.dirhams < cost:
            raise HTTPException(status_code=400, detail=f"Нужно {cost} дирхам(ов)")
        player.dirhams -= cost
        player.total_dirhams_spent += cost
        pb.auto_mode = "sell" if BUILDINGS[building_key]["category"] == "production" else "process"
        pb.auto_until = now_utc() + timedelta(hours=SETTINGS["auto_hours"])
    db.commit()
    return _serialize_state(db, player)


def send_caravan(db: Session, telegram_id: str, route_key: str, guard_level: str, resource_key: str, amount: float) -> dict:
    if route_key not in CARAVAN_ROUTES:
        raise HTTPException(status_code=400, detail="Неизвестный маршрут")
    if guard_level not in GUARDS:
        raise HTTPException(status_code=400, detail="Неизвестный уровень охраны")
    if resource_key not in RESOURCES:
        raise HTTPException(status_code=400, detail="Неизвестный ресурс")
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    active_count = sum(1 for c in player.caravans if not c.resolved)
    if active_count >= SETTINGS["max_active_caravans"]:
        raise HTTPException(status_code=400, detail=f"Максимум {SETTINGS['max_active_caravans']} активных караванов")
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
    db.add(Caravan(player=player, route_key=route_key, guard_level=guard_level, cargo_json=json.dumps({resource_key: amount}, ensure_ascii=False), cargo_value=cargo_value, expected_profit=round(expected_profit, 2), risk_percent=risk, ends_at=now_utc() + timedelta(seconds=duration_seconds), status="traveling"))
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
    if success:
        gold = round(caravan.expected_profit, 2)
        if route.get("bonus_type") == "gold_bonus":
            gold *= (1 + route["bonus_value"])
        player.gold += gold
        player.total_gold_earned += gold
        player.total_caravans_success += 1
        player.total_caravan_profit += gold
        caravan.result_gold = gold
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
    player.dirhams += reward_dirhams
    player.free_chest_ready_at = now + timedelta(seconds=SETTINGS["free_chest_cooldown_seconds"])
    db.commit()
    return _serialize_state(db, player)
