from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
from urllib.parse import parse_qsl

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
import threading

from .database import Base, engine, get_db
from .logic import (
    buy_building,
    buy_dirham,
    claim_caravan,
    get_or_create_player,
    hire_worker,
    fire_worker,
    make_state,
    mine_click,
    mine_upgrade,
    open_chest,
    process_resources,
    sell_resource,
    send_caravan,
    storage_upgrade,
    toggle_building_automation,
    upgrade_worker,
)
from .schemas import (
    AuthRequest,
    BuildingActionRequest,
    BuildingAutomationRequest,
    CaravanClaimRequest,
    CaravanSendRequest,
    ChestOpenRequest,
    DirhamBuyRequest,
    MineClickRequest,
    MineUpgradeRequest,
    ProcessRequest,
    SellRequest,
    StorageUpgradeRequest,
    TelegramAuthRequest,
    WorkerHireRequest,
    WorkerUpgradeRequest,
    WorkerFireRequest,
)

Base.metadata.create_all(bind=engine)


def _safe_add_column(table: str, col_sql: str) -> None:
    try:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_sql}"))
    except Exception:
        pass


_safe_add_column("players", "mine_pickaxe_level INTEGER DEFAULT 0")
_safe_add_column("player_buildings", "auto_mode VARCHAR(16) DEFAULT 'off'")
_safe_add_column("player_buildings", "auto_until DATETIME")
_safe_add_column("players", "pets_found INTEGER DEFAULT 0")
_safe_add_column("players", "active_pet_key VARCHAR(64)")

app = FastAPI(title="Steppe Tycoon", version="7.5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

_mine_locks: dict[str, threading.Lock] = {}
_mine_locks_guard = threading.Lock()


def _get_mine_lock(telegram_id: str) -> threading.Lock:
    with _mine_locks_guard:
        lock = _mine_locks.get(telegram_id)
        if lock is None:
            lock = threading.Lock()
            _mine_locks[telegram_id] = lock
        return lock


def _validate_telegram_init_data(init_data: str) -> dict:
    if not init_data:
        raise HTTPException(status_code=400, detail="Пустые Telegram init data")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        raise HTTPException(status_code=500, detail="На сервере не задан TELEGRAM_BOT_TOKEN")
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=400, detail="Отсутствует hash в init data")
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(key=b"WebAppData", msg=bot_token.encode("utf-8"), digestmod=hashlib.sha256).digest()
    calculated_hash = hmac.new(key=secret_key, msg=data_check_string.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(status_code=401, detail="Невалидные Telegram init data")
    user_raw = pairs.get("user")
    if not user_raw:
        raise HTTPException(status_code=400, detail="В init data нет user")
    try:
        user_data = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Некорректный user в init data") from exc
    if "id" not in user_data:
        raise HTTPException(status_code=400, detail="В Telegram user отсутствует id")
    return user_data


@app.get("/api/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/api/auth")
def auth(payload: AuthRequest, db: Session = Depends(get_db)) -> dict:
    player = get_or_create_player(db, payload.telegram_id, payload.username)
    return make_state(db, player.telegram_id)


@app.post("/api/auth/telegram")
def auth_telegram(payload: TelegramAuthRequest, db: Session = Depends(get_db)) -> dict:
    user_data = _validate_telegram_init_data(payload.init_data)
    telegram_id = str(user_data["id"])
    username = user_data.get("username") or user_data.get("first_name") or user_data.get("last_name") or "Игрок"
    player = get_or_create_player(db, telegram_id, username)
    return make_state(db, player.telegram_id)


@app.get("/api/state/{telegram_id}")
def state(telegram_id: str, db: Session = Depends(get_db)) -> dict:
    return make_state(db, telegram_id)


@app.post("/api/building/buy")
def api_buy_building(payload: BuildingActionRequest, db: Session = Depends(get_db)) -> dict:
    return buy_building(db, payload.telegram_id, payload.building_key)


@app.post("/api/building/automation")
def api_building_automation(payload: BuildingAutomationRequest, db: Session = Depends(get_db)) -> dict:
    return toggle_building_automation(db, payload.telegram_id, payload.building_key)


@app.post("/api/worker/hire")
def api_hire_worker(payload: WorkerHireRequest, db: Session = Depends(get_db)) -> dict:
    return hire_worker(db, payload.telegram_id, payload.worker_key)


@app.post("/api/worker/upgrade")
def api_upgrade_worker(payload: WorkerUpgradeRequest, db: Session = Depends(get_db)) -> dict:
    return upgrade_worker(db, payload.telegram_id, payload.upgrade_key)


@app.post("/api/worker/fire")
def api_fire_worker(payload: WorkerFireRequest, db: Session = Depends(get_db)) -> dict:
    return fire_worker(db, payload.telegram_id, payload.worker_key)


@app.post("/api/process")
def api_process(payload: ProcessRequest, db: Session = Depends(get_db)) -> dict:
    return process_resources(db, payload.telegram_id, payload.recipe_key, payload.amount)


@app.post("/api/sell")
def api_sell(payload: SellRequest, db: Session = Depends(get_db)) -> dict:
    return sell_resource(db, payload.telegram_id, payload.resource_key, payload.amount)


@app.post("/api/dirham/buy")
def api_buy_dirham(payload: DirhamBuyRequest, db: Session = Depends(get_db)) -> dict:
    return buy_dirham(db, payload.telegram_id)


@app.post("/api/storage/upgrade")
def api_storage_upgrade(payload: StorageUpgradeRequest, db: Session = Depends(get_db)) -> dict:
    return storage_upgrade(db, payload.telegram_id)


@app.post("/api/mine/click")
def api_mine_click(payload: MineClickRequest, db: Session = Depends(get_db)) -> dict:
    lock = _get_mine_lock(payload.telegram_id)
    with lock:
        try:
            return mine_click(db, payload.telegram_id)
        except OperationalError as exc:
            db.rollback()
            raise HTTPException(status_code=503, detail="Шахта занята, попробуй ещё раз") from exc


@app.post("/api/mine/upgrade")
def api_mine_upgrade(payload: MineUpgradeRequest, db: Session = Depends(get_db)) -> dict:
    return mine_upgrade(db, payload.telegram_id, payload.upgrade_type)


@app.post("/api/caravan/send")
def api_send_caravan(payload: CaravanSendRequest, db: Session = Depends(get_db)) -> dict:
    return send_caravan(db, payload.telegram_id, payload.route_key, payload.guard_level, payload.resource_key, payload.amount)


@app.post("/api/caravan/claim")
def api_claim_caravan(payload: CaravanClaimRequest, db: Session = Depends(get_db)) -> dict:
    return claim_caravan(db, payload.telegram_id, payload.caravan_id)


@app.post("/api/chest/open")
def api_open_chest(payload: ChestOpenRequest, db: Session = Depends(get_db)) -> dict:
    return open_chest(db, payload.telegram_id)


@app.get("/")
def root() -> FileResponse:
    return FileResponse(str(FRONTEND_DIR / "index.html"))
