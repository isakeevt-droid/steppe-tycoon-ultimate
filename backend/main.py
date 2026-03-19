from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .logic import (
    buy_building,
    buy_dirham,
    claim_caravan,
    get_or_create_player,
    hire_worker,
    make_state,
    mine_click,
    mine_upgrade,
    open_chest,
    process_resources,
    sell_resource,
    send_caravan,
    storage_upgrade,
    upgrade_worker,
)
from .schemas import (
    AuthRequest,
    BuildingActionRequest,
    CaravanClaimRequest,
    CaravanSendRequest,
    ChestOpenRequest,
    DirhamBuyRequest,
    MineClickRequest,
    MineUpgradeRequest,
    ProcessRequest,
    SellRequest,
    StorageUpgradeRequest,
    WorkerHireRequest,
    WorkerUpgradeRequest,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Steppe Tycoon", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"

app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/auth")
def auth(payload: AuthRequest, db: Session = Depends(get_db)):
    player = get_or_create_player(db, payload.telegram_id, payload.username)
    return make_state(db, player.telegram_id)


@app.get("/api/state/{telegram_id}")
def state(telegram_id: str, db: Session = Depends(get_db)):
    return make_state(db, telegram_id)


@app.post("/api/building/buy")
def api_buy_building(payload: BuildingActionRequest, db: Session = Depends(get_db)):
    return buy_building(db, payload.telegram_id, payload.building_key)


@app.post("/api/worker/hire")
def api_hire_worker(payload: WorkerHireRequest, db: Session = Depends(get_db)):
    return hire_worker(db, payload.telegram_id, payload.worker_key)


@app.post("/api/worker/upgrade")
def api_upgrade_worker(payload: WorkerUpgradeRequest, db: Session = Depends(get_db)):
    return upgrade_worker(db, payload.telegram_id, payload.upgrade_key)


@app.post("/api/process")
def api_process(payload: ProcessRequest, db: Session = Depends(get_db)):
    return process_resources(db, payload.telegram_id, payload.recipe_key, payload.amount)


@app.post("/api/sell")
def api_sell(payload: SellRequest, db: Session = Depends(get_db)):
    return sell_resource(db, payload.telegram_id, payload.resource_key, payload.amount)


@app.post("/api/dirham/buy")
def api_buy_dirham(payload: DirhamBuyRequest, db: Session = Depends(get_db)):
    return buy_dirham(db, payload.telegram_id)


@app.post("/api/storage/upgrade")
def api_storage_upgrade(payload: StorageUpgradeRequest, db: Session = Depends(get_db)):
    return storage_upgrade(db, payload.telegram_id)


@app.post("/api/mine/click")
def api_mine_click(payload: MineClickRequest, db: Session = Depends(get_db)):
    return mine_click(db, payload.telegram_id)


@app.post("/api/mine/upgrade")
def api_mine_upgrade(payload: MineUpgradeRequest, db: Session = Depends(get_db)):
    return mine_upgrade(db, payload.telegram_id)


@app.post("/api/caravan/send")
def api_send_caravan(payload: CaravanSendRequest, db: Session = Depends(get_db)):
    return send_caravan(
        db,
        payload.telegram_id,
        payload.route_key,
        payload.guard_level,
        payload.resource_key,
        payload.amount,
    )


@app.post("/api/caravan/claim")
def api_claim_caravan(payload: CaravanClaimRequest, db: Session = Depends(get_db)):
    return claim_caravan(db, payload.telegram_id, payload.caravan_id)


@app.post("/api/chest/open")
def api_open_chest(payload: ChestOpenRequest, db: Session = Depends(get_db)):
    return open_chest(db, payload.telegram_id)


@app.get("/")
def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))