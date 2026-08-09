"""
Upsert helpers for the write pattern the server actually needs: every
poll cycle, for every aircraft seen, "insert this row, or update it if
it already exists" — in one round trip, not a SELECT followed by an
INSERT-or-UPDATE.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Aircraft, AircraftState, PositionHistory


async def upsert_aircraft(
    session: AsyncSession,
    hex_code: str,
    registration: str | None = None,
    aircraft_type: str | None = None,
) -> None:
    """
    Insert-or-touch the aircraft identity row. Only overwrites
    registration/aircraft_type when a non-None value is actually
    provided — these are slow-changing airframe attributes, so a poll
    that doesn't happen to report them (e.g. a partial API response)
    should not wipe out a value already known.
    """
    # Explicitly typed dict[str, Any]: a single-key literal like
    # `{"last_seen": func.now()}` would otherwise get inferred from
    # that one value's type alone, then reject the later string
    # assignments below as a type mismatch.
    values: dict[str, Any] = {"hex": hex_code, "last_seen": func.now()}
    update: dict[str, Any] = {"last_seen": func.now()}
    if registration is not None:
        values["registration"] = registration
        update["registration"] = registration
    if aircraft_type is not None:
        values["aircraft_type"] = aircraft_type
        update["aircraft_type"] = aircraft_type

    stmt = sqlite_insert(Aircraft).values(**values)
    stmt = stmt.on_conflict_do_update(index_elements=["hex"], set_=update)
    await session.execute(stmt)


async def upsert_aircraft_state(
    session: AsyncSession,
    hex_code: str,
    *,
    registration: str | None = None,
    aircraft_type: str | None = None,
    **state_fields,
) -> None:
    """
    Upsert both tables for one sighting: touches the aircraft identity
    row (see upsert_aircraft above) and overwrites aircraft_state with
    whatever volatile fields this sighting reported (callsign, squawk,
    position, etc. — pass only what's available; fields not passed
    are left untouched on update since state_fields only contains
    what was passed in).
    """
    await upsert_aircraft(
        session, hex_code, registration=registration, aircraft_type=aircraft_type
    )

    state_stmt = sqlite_insert(AircraftState).values(hex=hex_code, **state_fields)
    state_stmt = state_stmt.on_conflict_do_update(
        index_elements=["hex"], set_=state_fields
    )
    await session.execute(state_stmt)


async def record_position(session: AsyncSession, hex_code: str, **fields) -> None:
    """
    Append-only insert into position_history — unlike aircraft_state,
    this is a log, not a snapshot: every call adds a new row rather
    than overwriting the last one. Only call this for aircraft that
    actually need a trail (currently: favorites, from
    background_tasks.py) since it's unbounded growth for whatever
    hex it's called on.
    """
    session.add(PositionHistory(hex=hex_code, **fields))
