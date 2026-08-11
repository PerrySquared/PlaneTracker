"""
Flight-history endpoint backing the frontend's trail feature. Reads
from position_history (db/models.py) — only aircraft that have
actually been polled with persistence (currently: favorites, see
background_tasks.py) will have any rows here. Requesting history for
a hex that isn't/wasn't favorited just returns an empty points list,
not an error.
"""

import datetime as dt
import logging

from fastapi import APIRouter, Query
from sqlalchemy import select

from db.database import get_session
from db.models import PositionHistory

from ..config import CURRENT_FLIGHT_STALE_MINUTES, FLIGHT_GAP_MINUTES, MAX_HISTORY_POINTS
from ..flight_segmentation import latest_flight_only, segment_flights

log = logging.getLogger("aircraft-server")

router = APIRouter(tags=["history"])


@router.get("/history/{hex_code}")
async def get_history(
    hex_code: str, scope: str = Query("current", pattern="^(current|full)$")
):
    hex_code = hex_code.lower()
    async with get_session() as session:
        result = await session.execute(
            select(PositionHistory)
            .where(PositionHistory.hex == hex_code)
            .order_by(PositionHistory.recorded_at.asc())
        )
        rows = result.scalars().all()

    if not rows:
        return {"hex": hex_code, "scope": scope, "points": []}

    segmented = segment_flights(rows, FLIGHT_GAP_MINUTES)

    if scope == "current":
        segmented = latest_flight_only(segmented)
        if segmented:
            age_minutes = (
                dt.datetime.now(dt.UTC) - segmented[-1].recorded_at.replace(tzinfo=dt.UTC)
            ).total_seconds() / 60
            if age_minutes > CURRENT_FLIGHT_STALE_MINUTES:
                # The most recent recorded flight is old enough to treat
                # as landed/transponder-off rather than ongoing with a
                # signal gap - don't surface it as "current". It's still
                # there under scope=full, this only affects this branch.
                segmented = []

    if len(segmented) > MAX_HISTORY_POINTS:
        segmented = segmented[-MAX_HISTORY_POINTS:]

    return {
        "hex": hex_code,
        "scope": scope,
        "points": [
            {
                "latitude": p.latitude,
                "longitude": p.longitude,
                "altitude_baro": p.altitude_baro,
                "callsign": p.callsign,
                "recorded_at": p.recorded_at.isoformat(),
                "flight_id": p.flight_id,
            }
            for p in segmented
        ],
    }
