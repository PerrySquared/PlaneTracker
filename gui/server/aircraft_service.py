"""
INTEGRATION POINT. This is the one file that should need editing to plug
in real data:
  - `aircraft_interface` below (required)
  - `get_current_aircraft()` (optional — see its docstring)

Everything downstream (routes, background polling, serialization) just
calls the two functions defined here.
"""

import logging
import time
from collections.abc import Iterable

from api.aircraft_information_interface import AircraftInformationInterface
from container import Container

log = logging.getLogger("aircraft-server")

# ---------------------------------------------------------------------------
# 0. INTEGRATION POINT — construct the interface with its real providers.
# ---------------------------------------------------------------------------
c = Container()
aircraft_interface = AircraftInformationInterface(providers=c.aircraft_information_apis)


def _require_interface():
    if aircraft_interface is None:
        raise RuntimeError(
            "aircraft_interface is not configured — set it up in "
            "aircraft_service.py with the providers before running."
        )


# ---------------------------------------------------------------------------
# 1. OPTIONAL INTEGRATION POINT — an "ambient" feed of whatever's currently
#    tracked, independent of search/favorites (e.g. everything the DB
#    has recently seen, if kept one populated separately).
#
#    AircraftInformationInterface.fetch_normalized_flight_data() takes a
#    required `search: list[str]`, which fits "look up these specific
#    hexes/callsigns/etc." (that's exactly what search_aircraft() and
#    favorites use it for below) but doesn't have an obvious "give me
#    everything currently in view" mode. So this is left as a separate,
#    unconfigured stub rather than guessing how — for a general sweep to
#    also go through aircraft_interface (e.g. some api_endpoint_select
#    value that means "all"), wire it the same way as search_aircraft()
#    below. Until then this just contributes nothing, and the map is
#    driven entirely by search results and favorites.
# ---------------------------------------------------------------------------
async def get_current_aircraft() -> Iterable:
    return []  # <-- ambient data source


# ---------------------------------------------------------------------------
# 1b. The single choke point for every outbound call to aircraft_interface
#     — both search_aircraft() (one value at a time, backing the explicit
#     search route) and background_tasks.py's favorites poll (many hexes
#     batched into one call) go through this, so logging/timing/error
#     handling only needs to live in one place instead of being
#     duplicated at each call site.
# ---------------------------------------------------------------------------
async def fetch_aircraft_data(search: list[str], api_endpoint_select: str) -> Iterable:
    _require_interface()
    start = time.monotonic()
    log.info("API fetch start: field=%s values=%s", api_endpoint_select, search)
    try:
        results = await aircraft_interface.fetch_normalized_flight_data(
            search=search, api_endpoint_select=api_endpoint_select
        )
    except Exception:
        elapsed_ms = (time.monotonic() - start) * 1000
        log.exception(
            "API fetch FAILED after %.0fms: field=%s values=%s",
            elapsed_ms,
            api_endpoint_select,
            search,
        )
        raise
    elapsed_ms = (time.monotonic() - start) * 1000
    log.info(
        "API fetch OK in %.0fms: field=%s values=%s -> %d result(s)",
        elapsed_ms,
        api_endpoint_select,
        search,
        len(results),
    )
    return results


# ---------------------------------------------------------------------------
# 1c. Search — thin wrapper around fetch_aircraft_data for a single
#     field/value lookup. Backs the explicit search route.
# ---------------------------------------------------------------------------
async def search_aircraft(field: str, value: str) -> Iterable:
    """
    `field` is one of "hex", "callsign", "reg", "type", "squawk" (already
    validated by the caller) and maps directly onto api_endpoint_select.
    """
    return await fetch_aircraft_data([value], field)
