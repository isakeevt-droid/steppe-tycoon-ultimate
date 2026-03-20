from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(64), default="Игрок")
    title_key: Mapped[str] = mapped_column(String(64), default="nomad")

    gold: Mapped[float] = mapped_column(Float, default=120.0)
    dirhams: Mapped[int] = mapped_column(Integer, default=0)

    storage_level: Mapped[int] = mapped_column(Integer, default=1)
    manual_mine_level: Mapped[int] = mapped_column(Integer, default=1)
    mine_pickaxe_level: Mapped[int] = mapped_column(Integer, default=0)

    total_gold_earned: Mapped[float] = mapped_column(Float, default=0.0)
    total_gold_spent: Mapped[float] = mapped_column(Float, default=0.0)
    total_resources_produced: Mapped[float] = mapped_column(Float, default=0.0)
    total_resources_processed: Mapped[float] = mapped_column(Float, default=0.0)
    total_caravans_sent: Mapped[int] = mapped_column(Integer, default=0)
    total_caravans_success: Mapped[int] = mapped_column(Integer, default=0)
    total_caravan_profit: Mapped[float] = mapped_column(Float, default=0.0)
    total_clicks: Mapped[int] = mapped_column(Integer, default=0)
    total_dirhams_bought: Mapped[int] = mapped_column(Integer, default=0)
    total_dirhams_spent: Mapped[int] = mapped_column(Float, default=0.0)

    dirhams_bought_today: Mapped[int] = mapped_column(Integer, default=0)
    dirham_day_key: Mapped[str] = mapped_column(String(16), default="")

    last_tick_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    free_chest_ready_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    buildings: Mapped[list["PlayerBuilding"]] = relationship(back_populates="player", cascade="all, delete-orphan")
    workers: Mapped[list["PlayerWorker"]] = relationship(back_populates="player", cascade="all, delete-orphan")
    resources: Mapped[list["PlayerResource"]] = relationship(back_populates="player", cascade="all, delete-orphan")
    achievements: Mapped[list["PlayerAchievement"]] = relationship(back_populates="player", cascade="all, delete-orphan")
    titles: Mapped[list["PlayerTitle"]] = relationship(back_populates="player", cascade="all, delete-orphan")
    caravans: Mapped[list["Caravan"]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
        order_by="Caravan.ends_at.desc()",
    )


class PlayerBuilding(Base):
    __tablename__ = "player_buildings"
    __table_args__ = (UniqueConstraint("player_id", "building_key", name="uq_player_building"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    building_key: Mapped[str] = mapped_column(String(64), index=True)
    level: Mapped[int] = mapped_column(Integer, default=0)
    auto_mode: Mapped[str] = mapped_column(String(16), default="off")
    auto_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    player: Mapped["Player"] = relationship(back_populates="buildings")


class PlayerWorker(Base):
    __tablename__ = "player_workers"
    __table_args__ = (UniqueConstraint("player_id", "worker_key", name="uq_player_worker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    worker_key: Mapped[str] = mapped_column(String(64), index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)

    player: Mapped["Player"] = relationship(back_populates="workers")


class PlayerResource(Base):
    __tablename__ = "player_resources"
    __table_args__ = (UniqueConstraint("player_id", "resource_key", name="uq_player_resource"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    resource_key: Mapped[str] = mapped_column(String(64), index=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)

    player: Mapped["Player"] = relationship(back_populates="resources")


class PlayerAchievement(Base):
    __tablename__ = "player_achievements"
    __table_args__ = (UniqueConstraint("player_id", "achievement_key", name="uq_player_achievement"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    achievement_key: Mapped[str] = mapped_column(String(64), index=True)
    unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    player: Mapped["Player"] = relationship(back_populates="achievements")


class PlayerTitle(Base):
    __tablename__ = "player_titles"
    __table_args__ = (UniqueConstraint("player_id", "title_key", name="uq_player_title"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    title_key: Mapped[str] = mapped_column(String(64), index=True)
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    player: Mapped["Player"] = relationship(back_populates="titles")


class Caravan(Base):
    __tablename__ = "caravans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    route_key: Mapped[str] = mapped_column(String(64), index=True)
    guard_level: Mapped[str] = mapped_column(String(32), default="none")
    cargo_json: Mapped[str] = mapped_column(String, default="{}")
    cargo_value: Mapped[float] = mapped_column(Float, default=0.0)
    expected_profit: Mapped[float] = mapped_column(Float, default=0.0)
    risk_percent: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ends_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(32), default="traveling")
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    result_gold: Mapped[float] = mapped_column(Float, default=0.0)
    result_dirhams: Mapped[int] = mapped_column(Integer, default=0)
    event_text: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    player: Mapped["Player"] = relationship(back_populates="caravans")
