"""
Flight-history endpoint backing the frontend's trail feature. Reads
from position_history (db/models.py) — only aircraft that have
actually been polled with persistence (currently: favorites, see
background_tasks.py) will have any rows here. Requesting history for
a hex that isn't/wasn't favorited just returns an empty points list,
not an error.
"""

import logging

from fastapi import APIRouter, Query
from sqlalchemy import select

from db.database import SessionLocal
from db.models import PositionHistory

from ..config import FLIGHT_GAP_MINUTES, MAX_HISTORY_POINTS
from ..flight_segmentation import latest_flight_only, segment_flights

log = logging.getLogger("aircraft-server")

router = APIRouter(tags=["history"])


@router.get("/history/{hex_code}")
async def get_history(
    hex_code: str, scope: str = Query("current", pattern="^(current|full)$")
):
    hex_code = hex_code.lower()
    async with SessionLocal() as session:
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
