"""
INTEGRATION POINT. This is the one file that should need editing to plug
in real data:
  - `aircraft_interface` below (required)
  - `get_current_aircraft()` (optional — see its docstring)

Everything downstream (routes, background polling, serialization) just
calls the two functions defined here.
"""

import logging
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
# 1b. Search — thin wrapper around AircraftInformationInterface for a
#     single field/value lookup. Backs both the explicit search route and
#     (in batched form) the favorites polling in background_tasks.py.
# ---------------------------------------------------------------------------
async def search_aircraft(field: str, value: str) -> Iterable:
    """
    `field` is one of "hex", "callsign", "reg", "type", "squawk" (already
    validated by the caller) and maps directly onto api_endpoint_select.
    """
    _require_interface()
    return await aircraft_interface.fetch_normalized_flight_data(
        search=[value], api_endpoint_select=field
    )
