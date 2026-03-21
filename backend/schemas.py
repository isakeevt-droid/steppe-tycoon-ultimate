from __future__ import annotations

from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    telegram_id: str = Field(min_length=1, max_length=64)
    username: str | None = None


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(min_length=1)


class BuildingActionRequest(BaseModel):
    telegram_id: str
    building_key: str


class BuildingAutomationRequest(BaseModel):
    telegram_id: str
    building_key: str


class WorkerHireRequest(BaseModel):
    telegram_id: str
    worker_key: str


class WorkerUpgradeRequest(BaseModel):
    telegram_id: str
    upgrade_key: str


class WorkerFireRequest(BaseModel):
    telegram_id: str
    worker_key: str


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
    upgrade_type: str = "mine"


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
