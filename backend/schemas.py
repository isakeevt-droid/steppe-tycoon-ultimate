
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    telegram_id: str = Field(min_length=1, max_length=64)
    username: str | None = None


class BuildingActionRequest(BaseModel):
    telegram_id: str
    building_key: str


class WorkerHireRequest(BaseModel):
    telegram_id: str
    worker_key: str


class WorkerUpgradeRequest(BaseModel):
    telegram_id: str
    upgrade_key: str


class ProcessRequest(BaseModel):
    telegram_id: str
    recipe_key: str
    amount: float = Field(gt=0)


class SellRequest(BaseModel):
    telegram_id: str
    resource_key: str
    amount: float = Field(gt=0)


class DirhamBuyRequest(BaseModel):
    telegram_id: str


class StorageUpgradeRequest(BaseModel):
    telegram_id: str


class MineClickRequest(BaseModel):
    telegram_id: str


class MineUpgradeRequest(BaseModel):
    telegram_id: str


class CaravanSendRequest(BaseModel):
    telegram_id: str
    route_key: str
    guard_level: str
    resource_key: str
    amount: float = Field(gt=0)


class CaravanClaimRequest(BaseModel):
    telegram_id: str
    caravan_id: int


class ChestOpenRequest(BaseModel):
    telegram_id: str


class ActionResponse(BaseModel):
    ok: bool = True
    message: str
    state: dict[str, Any]


class PlayerSummary(BaseModel):
    telegram_id: str
    username: str
    gold: float
    dirhams: int
    title_key: str
    title_name: str
    rank_score: float
    storage_level: int
    storage_capacity: float
    storage_used: float
    total_bonus_pct: float
    mine_level: int

    model_config = {"from_attributes": True}


class StateResponse(BaseModel):
    player: dict[str, Any]
    buildings: list[dict[str, Any]]
    workers: list[dict[str, Any]]
    resources: list[dict[str, Any]]
    caravan_routes: list[dict[str, Any]]
    active_caravans: list[dict[str, Any]]
    achievements: list[dict[str, Any]]
    titles: list[dict[str, Any]]
    leaderboard: list[dict[str, Any]]
    market_prices: dict[str, float]
    server_time: datetime
    tooltips: dict[str, str]
