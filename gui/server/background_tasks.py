"""
Long-running loops kicked off at startup (see main.py's lifespan):
broadcasting merged aircraft state to connected clients, and refreshing
the favorites cache (and persisting it to the DB) on its own slower
cadence.
"""

import asyncio
import json
import logging

from db.database import get_session
from db.upserts import record_position, upsert_aircraft_state

from . import state
from .aircraft_service import fetch_aircraft_data, get_current_aircraft
from .config import (
    BROADCAST_INTERVAL_SECONDS,
    FAVORITES_POLL_INTERVAL_SECONDS,
    PROVIDER_FETCH_FAILED_HINT,
)
from .serialization import serialize_aircraft
from .state import (
    favorite_cache,
    favorite_cache_lock,
    favorites,
    manager,
)

log = logging.getLogger("aircraft-server")


async def broadcast_loop():
    while True:
        try:
            merged: dict[str, dict] = {}
            for a in await get_current_aircraft():
                d = serialize_aircraft(a)
                hex_code = (d.get("icao24") or "").lower()
                if hex_code:
                    merged[hex_code] = d

            # Fill in any favorites the general poll didn't happen to cover
            # (e.g. outside whatever area/filter get_current_aircraft applies)
            # from the favorites poll cache.
            async with favorite_cache_lock:
                for hex_code, d in favorite_cache.items():
                    merged.setdefault(hex_code, d)

            fav_set = set(await favorites.list())
            for hex_code, d in merged.items():
                d["is_favorite"] = hex_code in fav_set

            async with state.favorites_fetch_error_lock:
                fetch_error = state.favorites_fetch_error

            payload_obj: dict = {"aircraft": list(merged.values())}
            if fetch_error:
                payload_obj["favorites_fetch_error"] = fetch_error

            payload = json.dumps(payload_obj)
            await manager.broadcast(payload)
        except Exception:
            log.exception("Error while broadcasting aircraft")
        await asyncio.sleep(BROADCAST_INTERVAL_SECONDS)


async def _fetch_favorite_states(fav_hexes: list[str]) -> dict[str, dict]:
    """
    Looks up every favorited hex in one call — fetch_normalized_flight_data()
    takes `search` as a list, so N favorites are combined into a single API call,
    as long as the provider's underlying endpoint actually honors a
    multi-value hex lookup in one request. If it doesn't (i.e. it only
    honors the first value in the list), splits this back into a per-hex
    loop.

    Returns {} — rather than raising — on any failure, since a failed
    poll should just mean "nothing fresh this cycle," not stop the loop.
    """
    if not fav_hexes:
        async with state.favorites_fetch_error_lock:
            state.favorites_fetch_error = None
        return {}
    try:
        results = await fetch_aircraft_data(fav_hexes, "hex")
    except Exception:
        log.warning(
            "Favorites poll got nothing this cycle (fetch failed) for hexes=%s", fav_hexes
        )
        async with state.favorites_fetch_error_lock:
            state.favorites_fetch_error = f"Could not refresh favorites from any provider. {PROVIDER_FETCH_FAILED_HINT}"
        return {}

    async with state.favorites_fetch_error_lock:
        state.favorites_fetch_error = None

    fresh: dict[str, dict] = {}
    for a in results:
        d = serialize_aircraft(a)
        if d.get("icao24"):
            fresh[d["icao24"].lower()] = d
    return fresh


async def _persist_favorite_states(fresh: dict[str, dict]) -> None:
    """
    Writes one poll cycle's worth of favorite state to the DB: an
    aircraft_state upsert for every entry, plus a position_history row
    for whichever ones actually have a position (a separate call since
    state overwrites in place while position_history appends a
    permanent log row — that's what backs the trail feature).

    A write failure here is logged and swallowed rather than raised —
    the in-memory favorite_cache (already updated by the caller before
    this runs) is what keeps the live UI working, so a DB hiccup
    shouldn't take that down too.
    """
    if not fresh:
        return
    try:
        async with get_session() as session:
            for hex_code, d in fresh.items():
                await upsert_aircraft_state(
                    session,
                    hex_code,
                    registration=d.get("registration"),
                    aircraft_type=d.get("aircraft_type"),
                    callsign=d.get("callsign"),
                    squawk=d.get("squawk"),
                    latitude=d.get("latitude"),
                    longitude=d.get("longitude"),
                    altitude_baro=d.get("altitude_baro"),
                    rate_baro=d.get("rate_baro"),
                    ground_speed=d.get("ground_speed"),
                    track=d.get("track"),
                )
                if d.get("latitude") is not None and d.get("longitude") is not None:
                    await record_position(
                        session,
                        hex_code,
                        callsign=d.get("callsign"),
                        squawk=d.get("squawk"),
                        latitude=d.get("latitude"),
                        longitude=d.get("longitude"),
                        altitude_baro=d.get("altitude_baro"),
                    )

    except Exception:
        log.exception("Could not persist favorites poll results to DB")


async def favorites_poll_loop():
    """
    The "always polled" half of favorites: independently of whatever
    get_current_aircraft() returns, actively look up every favorited hex
    (see _fetch_favorite_states) so favorites keep showing up even if
    they fall outside the normal ambient feed's scope (if there is one),
    then persist that cycle's results to the DB (see
    _persist_favorite_states).

    Runs on its own slower cadence (FAVORITES_POLL_INTERVAL_SECONDS),
    decoupled from BROADCAST_INTERVAL_SECONDS, so a snappier UI refresh
    rate doesn't quietly multiply the API call rate or the DB write rate
    — the broadcast loop stays read-only against the in-memory cache.
    """
    while True:
        try:
            fav_hexes = await favorites.list()
            fresh = await _fetch_favorite_states(fav_hexes)

            async with favorite_cache_lock:
                favorite_cache.clear()
                favorite_cache.update(fresh)

            await _persist_favorite_states(fresh)
        except Exception:
            log.exception("Error while polling favorites")
        await asyncio.sleep(FAVORITES_POLL_INTERVAL_SECONDS)
