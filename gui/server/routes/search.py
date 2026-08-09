"""
Search — one-shot, called only when the user explicitly searches. Never
invoked on a timer or on every keystroke, so it can't itself run up the
API usage the way a live poll would.
"""

import logging

from fastapi import APIRouter, HTTPException

from ..aircraft_service import search_aircraft
from ..config import SEARCH_FIELDS
from ..serialization import serialize_aircraft
from ..state import favorites

log = logging.getLogger("aircraft-server")

router = APIRouter(tags=["search"])


@router.get("/search/{field}/{value}")
async def search(field: str, value: str):
    if field not in SEARCH_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown search field '{field}'. Must be one of {sorted(SEARCH_FIELDS)}.",
        )
    try:
        results = await search_aircraft(field, value)
    except Exception:
        log.exception("Search failed for %s=%s", field, value)
        raise HTTPException(
            status_code=502, detail="Search request to upstream source failed."
        )

    fav_set = set(await favorites.list())
    out = []
    for a in results:
        d = serialize_aircraft(a)
        d["is_favorite"] = (d.get("icao24") or "").lower() in fav_set
        out.append(d)
    return {"results": out}
