"""
SQLAlchemy ORM models for the aircraft tracker's SQLite database.

Layout:
  - Aircraft: one row per airframe, keyed by hex (ICAO24) — the only
    genuine identity column. Slow-changing (registration, type).
  - AircraftState: one row per aircraft, overwritten on every position
    update. Split out from Aircraft (rather than folding these columns
    in) so the high-frequency writes here don't touch Aircraft's own
    row or its indexes.
  - PositionHistory: optional append-only log — only include this if
    track replay is actually needed, not just "where is it right now."
  - Favorite: replaces favorites_store.py's JSON file.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Float, ForeignKey, Index, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Model(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class Aircraft(Model):
    __tablename__ = "aircraft"

    hex: Mapped[str] = mapped_column(String(6), primary_key=True)
    registration: Mapped[str | None] = mapped_column(String(16), index=True)
    aircraft_type: Mapped[str | None] = mapped_column(String(8), index=True)
    first_seen: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    last_seen: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    state: Mapped[AircraftState | None] = relationship(
        back_populates="aircraft", uselist=False, cascade="all, delete-orphan"
    )
    history: Mapped[list[PositionHistory]] = relationship(
        back_populates="aircraft", cascade="all, delete-orphan"
    )
    favorite: Mapped[Favorite | None] = relationship(
        back_populates="aircraft", uselist=False, cascade="all, delete-orphan"
    )


class AircraftState(Model):
    __tablename__ = "aircraft_state"

    hex: Mapped[str] = mapped_column(
        ForeignKey("aircraft.hex", ondelete="CASCADE"), primary_key=True
    )
    callsign: Mapped[str | None] = mapped_column(String(8), index=True)
    squawk: Mapped[str | None] = mapped_column(String(4), index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    altitude_baro: Mapped[float | None] = mapped_column(Float)
    rate_baro: Mapped[float | None] = mapped_column(Float)
    ground_speed: Mapped[float | None] = mapped_column(Float)
    track: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    aircraft: Mapped[Aircraft] = relationship(back_populates="state")


class PositionHistory(Model):
    """Append-only log backing the trail feature — one row per
    position_history write (see db/upserts.py's record_position),
    currently written once per favorites-poll cycle for each favorite
    (see background_tasks.py)."""

    __tablename__ = "position_history"
    __table_args__ = (Index("idx_history_hex_time", "hex", "recorded_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hex: Mapped[str] = mapped_column(ForeignKey("aircraft.hex", ondelete="CASCADE"))
    callsign: Mapped[str | None] = mapped_column(String(8))
    squawk: Mapped[str | None] = mapped_column(String(4))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    altitude_baro: Mapped[float | None] = mapped_column(Float)
    recorded_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    aircraft: Mapped[Aircraft] = relationship(back_populates="history")


class Favorite(Model):
    __tablename__ = "favorites"

    hex: Mapped[str] = mapped_column(
        ForeignKey("aircraft.hex", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    aircraft: Mapped[Aircraft] = relationship(back_populates="favorite")
