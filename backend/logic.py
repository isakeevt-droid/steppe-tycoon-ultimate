from __future__ import annotations

import json
import random
from datetime import timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .content import ACHIEVEMENTS, BUILDINGS, CARAVAN_ROUTES, GUARDS, PETS, PROCESSING_RECIPES, RESOURCES, SETTINGS, TITLES, WORKERS, WORKER_UPGRADES
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
    money,
    get_next_title,
    get_title_bonus_pct,
    now_utc,
)
from .models import Caravan, Player, PlayerAchievement, PlayerBuilding, PlayerResource, PlayerTitle, PlayerWorker



EPSILON = 1e-6


def _money(value: float) -> float:
    return round(float(value or 0.0), 2)


def _gold_lt(current: float, required: float) -> bool:
    return _money(current) + EPSILON < _money(required)


def _add_gold(player: Player, amount: float) -> float:
    amount = _money(amount)
    player.gold = _money(player.gold + amount)
    player.total_gold_earned = _money(player.total_gold_earned + amount)
    return amount


def _spend_gold(player: Player, amount: float) -> float:
    amount = _money(amount)
    if _gold_lt(player.gold, amount):
        raise HTTPException(status_code=400, detail="Недостаточно золота")
    player.gold = _money(player.gold - amount)
    player.total_gold_spent = _money(player.total_gold_spent + amount)
    return amount

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


def _pet_bonus_pct(player: Player) -> float:
    if not player.active_pet_key:
        return 0.0
    pet = PETS.get(player.active_pet_key)
    if not pet:
        return 0.0
    return float(pet.get("bonus_pct", 0.0))


def _chest_rewards_preview() -> dict:
    pet_drop = max(float(SETTINGS.get("chest_pet_drop_chance", 0.0)), max((float(p.get("drop_chance", 0.0)) for p in PETS.values()), default=0.0))
    return {
        "gold_min": int(SETTINGS.get("chest_gold_min", 40)),
        "gold_max": int(SETTINGS.get("chest_gold_max", 90)),
        "dirham_chance_pct": round(float(SETTINGS.get("chest_dirham_chance", 0.35)) * 100, 1),
        "pet_drop_chance_pct": round(pet_drop * 100, 1),
        "pets": [
            {
                "key": key,
                "name": value["name"],
                "emoji": value.get("emoji", "🐾"),
                "bonus_pct": float(value.get("bonus_pct", 0.0)),
                "description": value.get("description", ""),
            }
            for key, value in PETS.items()
        ],
    }


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


def _money(value: object):
    return money(value)


def _money_float(value: object) -> float:
    return float(_money(value))


def _mul_money(left: object, right: object):
    return _money(Decimal(str(left)) * Decimal(str(right)))


def _has_enough_gold(player: Player, cost: object) -> bool:
    return _money(player.gold) >= _money(cost)


def _add_gold(player: Player, amount: object) -> None:
    amount_money = _money(amount)
    player.gold = _money_float(_money(player.gold) + amount_money)
    player.total_gold_earned = _money_float(_money(player.total_gold_earned) + amount_money)


def _spend_gold(player: Player, amount: object) -> None:
    amount_money = _money(amount)
    player.gold = _money_float(_money(player.gold) - amount_money)
    player.total_gold_spent = _money_float(_money(player.total_gold_spent) + amount_money)


def _auto_active(pb: PlayerBuilding, now=None) -> bool:
    now = now or now_utc()
    return pb.auto_until is not None and pb.auto_until > now and pb.auto_mode != "off"

def _auto_elapsed(player: Player, pb: PlayerBuilding, elapsed: float, now) -> float:
    if not _auto_active(pb, now):
        return 0.0
    if pb.auto_until is None:
        return 0.0
    return min(elapsed, max(0.0, (pb.auto_until - player.last_tick_at).total_seconds()))



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
    salary_due = _money(Decimal(str(salary_per_minute)) * Decimal(str(elapsed / 60.0)))
    payroll_ok = _money(player.gold) >= salary_due
    if salary_due > 0:
        paid = _money(min(_money(player.gold), salary_due))
        if paid > 0:
            _spend_gold(player, paid)

    achievement_bonus = _achievement_bonus_pct(player)
    title_bonus = get_title_bonus_pct(player.title_key)
    pet_bonus = _pet_bonus_pct(player)
    global_bonus = calculate_global_bonus_pct(achievement_bonus, title_bonus + pet_bonus)
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
        player.total_resources_produced = round(float(player.total_resources_produced or 0.0) + float(actual), 4)

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
        if amount <= 0:
            continue
        input_res.amount -= amount
        output_res.amount += amount
        player.total_resources_processed = round(float(player.total_resources_processed or 0.0) + float(amount), 4)

    # automation: faster auto-sale for production and faster auto-processing + auto-sale for processing
    auto_sell_speed = float(SETTINGS.get("auto_sell_speed_multiplier", 1.0))
    auto_process_speed = float(SETTINGS.get("auto_process_speed_multiplier", 1.0))

    for pb in player.buildings:
        cfg = BUILDINGS[pb.building_key]
        if pb.level <= 0:
            continue

        active_elapsed = _auto_elapsed(player, pb, elapsed, now)
        if active_elapsed <= 0:
            continue

        if cfg["category"] == "production":
            res = resources[cfg["resource_key"]]
            if res.amount <= 0:
                continue
            auto_sell_per_sec = calculate_building_output_per_second(
                pb.building_key,
                pb.level,
                worker_bonus,
                global_bonus,
                payroll_ok,
            ) * auto_sell_speed
            sell_amount = min(res.amount, round(auto_sell_per_sec * active_elapsed, 4))
            if sell_amount <= 0:
                continue
            market_price = calculate_market_price(cfg["resource_key"], market_seed)
            total = _mul_money(sell_amount, market_price)
            res.amount -= sell_amount
            _add_gold(player, total)
            continue

        if cfg["category"] == "processing":
            # Extra auto-processing on top of passive processing
            per_sec = calculate_processing_output_per_second(pb.level, cfg.get("batch_size", 10), worker_bonus, global_bonus, payroll_ok)
            bonus_multiplier = max(0.0, auto_process_speed - 1.0)
            extra_amount = round(max(0.0, per_sec * active_elapsed * bonus_multiplier), 4)
            if extra_amount > 0:
                input_res = resources[cfg["input_key"]]
                output_res = resources[cfg["output_key"]]
                extra_amount = min(extra_amount, input_res.amount)
                if extra_amount > 0:
                    input_res.amount -= extra_amount
                    output_res.amount += extra_amount
                    player.total_resources_processed = round(float(player.total_resources_processed or 0.0) + float(extra_amount), 4)

            if pb.auto_mode != "process_sell":
                continue

            # Auto-sell processed goods only in process_sell mode
            output_res = resources[cfg["output_key"]]
            if output_res.amount <= 0:
                continue
            auto_sell_per_sec = calculate_processing_output_per_second(
                pb.level,
                cfg.get("batch_size", 10),
                worker_bonus,
                global_bonus,
                payroll_ok,
            ) * auto_sell_speed
            sell_amount = min(output_res.amount, round(auto_sell_per_sec * active_elapsed, 4))
            if sell_amount <= 0:
                continue
            market_price = calculate_market_price(cfg["output_key"], market_seed)
            total = _mul_money(sell_amount, market_price)
            output_res.amount -= sell_amount
            _add_gold(player, total)

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
    pet_bonus = _pet_bonus_pct(player)
    total_bonus = achievement_bonus + title_bonus + pet_bonus
    market_seed = _market_seed()
    title_meta = next((t for t in TITLES if t["key"] == player.title_key), TITLES[0])
    next_title = get_next_title(player.title_key)
    rank_score = calculate_rank_score(player, total_building_levels=sum(x.level for x in player.buildings), worker_count=sum(x.count for x in player.workers))
    capacity = calculate_storage_capacity(player.storage_level)
    used = _storage_used(player)
    market_prices = {k: _money_float(calculate_market_price(k, market_seed)) for k in RESOURCES}
    worker_counts = _worker_counts(player)
    worker_bonus = calculate_worker_bonus(worker_counts)
    worker_salary_per_minute = calculate_worker_salary_per_minute(worker_counts)
    worker_total_count = sum(worker_counts.values())
    global_bonus = calculate_global_bonus_pct(achievement_bonus, title_bonus + pet_bonus)
    resources_map = _resource_map(player)
    now = now_utc()
    base_tap, avg_tap, crit_chance, crit_mult = calculate_mine_click_income(player.manual_mine_level, player.mine_pickaxe_level, achievement_bonus, title_bonus)

    buildings = []
    notifications = []
    for pb in sorted(player.buildings, key=lambda x: x.building_key):
        cfg = BUILDINGS[pb.building_key]
        price = _money_float(calculate_building_price(pb.building_key, pb.level))
        auto_active = _auto_active(pb, now)
        auto_seconds = max(0, int((pb.auto_until - now).total_seconds())) if pb.auto_until else 0
        auto_kind = "sell" if cfg["category"] == "production" else pb.auto_mode
        if pb.auto_until is not None and pb.auto_until <= now and pb.auto_mode != "off":
            notifications.append(f"{cfg['name']}: авто-режим остановлен.")
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
            "auto_mode": pb.auto_mode,
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
            "mine_upgrade_cost": _money_float(calculate_mine_upgrade_cost(player.manual_mine_level)),
            "pickaxe_upgrade_cost": _money_float(calculate_pickaxe_upgrade_cost(player.mine_pickaxe_level)),
            "mine_base_tap": _money_float(base_tap),
            "mine_income": _money_float(avg_tap),
            "mine_crit_chance": crit_chance,
            "mine_crit_multiplier": crit_mult,
            "dirham_price": _money_float(calculate_dirham_buy_price(player.dirhams_bought_today)),
            "dirham_daily_limit": SETTINGS["dirham_daily_limit"],
            "dirhams_bought_today": player.dirhams_bought_today,
            "storage_upgrade_cost": _money_float(calculate_storage_upgrade_cost(player.storage_level)),
            "worker_bonus_pct": round(worker_bonus * 100, 1),
            "worker_salary_per_minute": round(worker_salary_per_minute, 2),
            "worker_total_count": worker_total_count,
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
            "chest_description": "Сундук открывается бесплатно раз в 4 часа: внутри золото, шанс на дирхам и редкий шанс на питомца.",
            "chest_preview": _chest_rewards_preview(),
            "dirham_description": "Дирхамы — редкая валюта. Нужны для охраны караванов, автопродажи, автопереработки и улучшения работников.",
            "dirham_price_explainer": f"Цена за 1 дирхам. Сегодня куплено: {player.dirhams_bought_today}/{SETTINGS['dirham_daily_limit']}. После каждой покупки цена растёт.",
            "pet_bonus_pct": round(pet_bonus, 2),
            "pets_found": player.pets_found,
            "active_pet": ({
                "key": player.active_pet_key,
                "name": PETS[player.active_pet_key]["name"],
                "emoji": PETS[player.active_pet_key].get("emoji", "🐾"),
                "bonus_pct": PETS[player.active_pet_key].get("bonus_pct", 0.0),
                "description": PETS[player.active_pet_key].get("description", ""),
            } if player.active_pet_key in PETS else None),
        },
        "buildings": buildings,
        "resources": resources,
        "workers": [{"key": pw.worker_key, "name": WORKERS[pw.worker_key]["name"], "count": pw.count, "hire_cost": _money_float(calculate_worker_hire_cost(pw.worker_key)), "salary": WORKERS[pw.worker_key]["salary_per_minute"], "efficiency_bonus_pct": round(WORKERS[pw.worker_key]["efficiency_bonus"]*100,1), "description": WORKERS[pw.worker_key]["description"], "can_fire": pw.count > 0} for pw in sorted(player.workers, key=lambda x: x.worker_key)],
        "worker_upgrades": [{
            "key": upgrade_key,
            "from_key": cfg["from"],
            "from_name": WORKERS[cfg["from"]]["name"],
            "to_key": cfg["to"],
            "to_name": WORKERS[cfg["to"]]["name"],
            "cost_dirhams": cfg["cost_dirhams"],
            "available": next((w.count for w in player.workers if w.worker_key == cfg["from"]), 0) > 0,
        } for upgrade_key, cfg in WORKER_UPGRADES.items()],
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
    price = _money(calculate_building_price(building_key, pb.level))
    if not _has_enough_gold(player, price):
        raise HTTPException(status_code=400, detail="Недостаточно золота")
    _spend_gold(player, price)
    pb.level += 1
    db.commit()
    return _serialize_state(db, player)


def hire_worker(db: Session, telegram_id: str, worker_key: str) -> dict:
    if worker_key not in WORKERS:
        raise HTTPException(status_code=400, detail="Неизвестный тип работника")
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    price = _money(calculate_worker_hire_cost(worker_key))
    if not _has_enough_gold(player, price):
        raise HTTPException(status_code=400, detail="Недостаточно золота")
    _spend_gold(player, price)
    next(x for x in player.workers if x.worker_key == worker_key).count += 1
    db.commit()
    return _serialize_state(db, player)




def fire_worker(db: Session, telegram_id: str, worker_key: str) -> dict:
    if worker_key not in WORKERS:
        raise HTTPException(status_code=400, detail="Неизвестный тип работника")
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    worker = next(x for x in player.workers if x.worker_key == worker_key)
    if worker.count < 1:
        raise HTTPException(status_code=400, detail="Нет работника для увольнения")
    worker.count -= 1
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
    player.total_dirhams_spent = _money(player.total_dirhams_spent + cfg["cost_dirhams"])
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
    # 1 к 1 переработка не увеличивает занятое место на складе,
    # поэтому дополнительное свободное место не требуется.
    in_res.amount -= amount
    out_res.amount += amount
    player.total_resources_processed = round(float(player.total_resources_processed or 0.0) + float(amount), 4)
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
    total = _mul_money(amount, calculate_market_price(resource_key, _market_seed()))
    res.amount -= amount
    _add_gold(player, total)
    db.commit()
    return _serialize_state(db, player)


def buy_dirham(db: Session, telegram_id: str) -> dict:
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    if player.dirhams_bought_today >= SETTINGS["dirham_daily_limit"]:
        raise HTTPException(status_code=400, detail="Дневной лимит достигнут")
    price = _money(calculate_dirham_buy_price(player.dirhams_bought_today))
    if not _has_enough_gold(player, price):
        raise HTTPException(status_code=400, detail="Недостаточно золота")
    _spend_gold(player, price)
    player.dirhams += 1
    player.total_dirhams_bought += 1
    player.dirhams_bought_today += 1
    db.commit()
    return _serialize_state(db, player)


def storage_upgrade(db: Session, telegram_id: str) -> dict:
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    price = _money(calculate_storage_upgrade_cost(player.storage_level))
    if not _has_enough_gold(player, price):
        raise HTTPException(status_code=400, detail="Недостаточно золота")
    _spend_gold(player, price)
    player.storage_level += 1
    db.commit()
    return _serialize_state(db, player)


def mine_click(db: Session, telegram_id: str) -> dict:
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    base_tap, _, crit_chance, crit_mult = calculate_mine_click_income(player.manual_mine_level, player.mine_pickaxe_level, _achievement_bonus_pct(player), get_title_bonus_pct(player.title_key))
    is_crit = random.random() < (crit_chance / 100.0)
    income = _mul_money(base_tap, crit_mult if is_crit else 1.0)
    _add_gold(player, income)
    player.total_clicks += 1
    db.commit()
    state = _serialize_state(db, player)
    state["mine_click"] = {"income": _money_float(income), "critical": is_crit}
    return state


def mine_upgrade(db: Session, telegram_id: str, upgrade_type: str = "mine") -> dict:
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    if upgrade_type == "pickaxe":
        price = _money(calculate_pickaxe_upgrade_cost(player.mine_pickaxe_level))
        if not _has_enough_gold(player, price):
            raise HTTPException(status_code=400, detail="Недостаточно золота")
        _spend_gold(player, price)
        player.mine_pickaxe_level += 1
    else:
        price = _money(calculate_mine_upgrade_cost(player.manual_mine_level))
        if not _has_enough_gold(player, price):
            raise HTTPException(status_code=400, detail="Недостаточно золота")
        _spend_gold(player, price)
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

    category = BUILDINGS[building_key]["category"]
    if category == "production":
        if _auto_active(pb):
            pb.auto_mode = "off"
            pb.auto_until = None
        else:
            cost = calculate_auto_activation_cost(pb.level)
            if player.dirhams < cost:
                raise HTTPException(status_code=400, detail=f"Нужно {cost} дирхам(ов)")
            player.dirhams -= cost
            player.total_dirhams_spent = _money(player.total_dirhams_spent + cost)
            pb.auto_mode = "sell"
            pb.auto_until = now_utc() + timedelta(hours=SETTINGS["auto_hours"])
    else:
        if _auto_active(pb):
            pb.auto_mode = "off"
            pb.auto_until = None
        else:
            cost = calculate_auto_activation_cost(pb.level)
            if player.dirhams < cost:
                raise HTTPException(status_code=400, detail=f"Нужно {cost} дирхам(ов)")
            player.dirhams -= cost
            player.total_dirhams_spent = _money(player.total_dirhams_spent + cost)
            pb.auto_mode = "process_sell"
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
    cargo_value = _mul_money(amount, calculate_market_price(resource_key, _market_seed()))
    risk = max(0.0, route["risk_percent"] - guard["risk_reduction"])
    expected_profit = _money(Decimal(str(cargo_value)) * Decimal(str(1 + route["profit_bonus"])))
    duration_seconds = route["duration_seconds"]
    if route.get("bonus_type") == "time_reduction":
        duration_seconds = max(60, int(duration_seconds * (1 - route["bonus_value"])))
    resource.amount -= amount
    player.dirhams -= guard["cost_dirhams"]
    player.total_dirhams_spent = _money(player.total_dirhams_spent + guard["cost_dirhams"])
    player.total_caravans_sent += 1
    db.add(Caravan(player=player, route_key=route_key, guard_level=guard_level, cargo_json=json.dumps({resource_key: amount}, ensure_ascii=False), cargo_value=_money_float(cargo_value), expected_profit=_money_float(expected_profit), risk_percent=risk, ends_at=now_utc() + timedelta(seconds=duration_seconds), status="traveling"))
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
        gold = _money(caravan.expected_profit)
        if route.get("bonus_type") == "gold_bonus":
            gold = _money(Decimal(str(gold)) * Decimal(str(1 + route["bonus_value"])))
        _add_gold(player, gold)
        player.total_caravans_success += 1
        player.total_caravan_profit = round(float(player.total_caravan_profit or 0) + float(gold), 2)
        caravan.result_gold = gold
    db.commit()
    return _serialize_state(db, player)


def open_chest(db: Session, telegram_id: str) -> dict:
    player = _get_player(db, telegram_id)
    tick_player(db, player)
    now = now_utc()
    if player.free_chest_ready_at > now:
        raise HTTPException(status_code=400, detail="Сундук ещё не готов")

    reward_gold = random.randint(int(SETTINGS.get("chest_gold_min", 40)), int(SETTINGS.get("chest_gold_max", 90)))
    reward_dirhams = 1 if random.random() < float(SETTINGS.get("chest_dirham_chance", 0.35)) else 0

    dropped_pet_key = None
    if player.active_pet_key is None:
        candidates = []
        for pet_key, pet in PETS.items():
            chance = float(pet.get("drop_chance", SETTINGS.get("chest_pet_drop_chance", 0.05)))
            candidates.append((pet_key, chance))
        for pet_key, chance in candidates:
            if random.random() < chance:
                dropped_pet_key = pet_key
                break

    _add_gold(player, reward_gold)
    player.dirhams += reward_dirhams

    if dropped_pet_key:
        player.active_pet_key = dropped_pet_key
        player.pets_found += 1

    player.free_chest_ready_at = now + timedelta(seconds=SETTINGS["free_chest_cooldown_seconds"])
    db.commit()
    state = _serialize_state(db, player)
    state["chest_open"] = {
        "gold": reward_gold,
        "dirhams": reward_dirhams,
        "pet": ({
            "key": dropped_pet_key,
            "name": PETS[dropped_pet_key]["name"],
            "emoji": PETS[dropped_pet_key].get("emoji", "🐾"),
            "bonus_pct": PETS[dropped_pet_key].get("bonus_pct", 0.0),
        } if dropped_pet_key else None),
    }
    return state
