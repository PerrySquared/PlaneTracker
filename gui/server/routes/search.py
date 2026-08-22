"""
Search — one-shot, called only when the user explicitly searches. Never
invoked on a timer or on every keystroke, so it can't itself run up the
API usage the way a live poll would.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from container import providers_container

from ..aircraft_service import list_providers_info, search_aircraft
from ..config import PROVIDER_FETCH_FAILED_HINT, SEARCH_FIELDS
from ..serialization import serialize_aircraft
from ..state import favorites

log = logging.getLogger("aircraft-server")

router = APIRouter(tags=["search"])


@router.get("/providers")
async def list_providers():
    """Every configured provider's name and supported search fields,
    for the frontend's provider selector. "Auto" isn't included here —
    it's the frontend's own default for "omit provider entirely".
    """
    return {"providers": list_providers_info()}


@router.get("/search/{field}/{value}")
async def search(field: str, value: str, provider_name: str | None = Query(None)):
    if field not in SEARCH_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown search field '{field}'. Must be one of {sorted(SEARCH_FIELDS)}.",
        )

    provider_object = providers_container.get_provider_object_from_string(provider_name)

    try:
        results = await search_aircraft(field, value, provider=provider_object)
    except Exception:
        log.exception(
            "Search failed for %s=%s provider=%s", field, value, provider_name or "auto"
        )
        raise HTTPException(
            status_code=502,
            detail=f"Search request to upstream source failed. {PROVIDER_FETCH_FAILED_HINT}",
        )

    fav_set = set(await favorites.list())
    out = []
    for a in results:
        d = serialize_aircraft(a)
        d["is_favorite"] = (d.get("icao24") or "").lower() in fav_set
        out.append(d)
    return {"results": out}
