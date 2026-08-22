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
from api.providers.base import AircraftInformationBase
from container import providers_container

from .config import SEARCH_FIELDS

log = logging.getLogger("aircraft-server")

# ---------------------------------------------------------------------------
# 0. INTEGRATION POINT — construct the interface with its real providers.
# ---------------------------------------------------------------------------
aircraft_interface = AircraftInformationInterface(
    providers=providers_container.aircraft_information_apis
)


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
async def fetch_aircraft_data(
    search: list[str],
    api_endpoint_select: str,
    provider: AircraftInformationBase | None = None,
) -> Iterable:
    _require_interface()

    start = time.monotonic()
    log.info(
        "API fetch start: field=%s values=%s provider=%s",
        api_endpoint_select,
        search,
        provider or "auto",
    )

    try:
        results = await aircraft_interface.fetch_normalized_flight_data(
            search=search,
            api_endpoint_select=api_endpoint_select,
            provider=provider,
        )
    except Exception:
        elapsed_ms = (time.monotonic() - start) * 1000
        log.exception(
            "API fetch FAILED after %.0fms: field=%s values=%s provider=%s",
            elapsed_ms,
            api_endpoint_select,
            search,
            provider or "auto",
        )
        raise
    elapsed_ms = (time.monotonic() - start) * 1000

    log.info(
        "API fetch OK in %.0fms: field=%s values=%s provider=%s -> %d result(s)",
        elapsed_ms,
        api_endpoint_select,
        search,
        provider or "auto",
        len(results),
    )

    return results


# ---------------------------------------------------------------------------
# 1c. Search — thin wrapper around fetch_aircraft_data for a single
#     field/value lookup. Backs the explicit search route.
# ---------------------------------------------------------------------------
async def search_aircraft(
    field: str, value: str, provider: AircraftInformationBase | None = None
) -> Iterable:
    """
    `field` is one of "hex", "callsign", "reg", "type", "squawk" (already
    validated by the caller) and maps directly onto api_endpoint_select.
    `provider`, if given, restricts the search to that single configured
    provider with no fallback — see fetch_aircraft_data /
    AircraftInformationInterface.fetch_normalized_flight_data for what
    happens if it fails, or if it doesn't match anything configured.
    """
    return await fetch_aircraft_data([value], field, provider=provider)


def list_providers_info() -> list[dict]:
    """
    Name + supported search fields for every configured provider, for
    the frontend's provider selector (which also filters the endpoint
    selector down to what's actually usable once a specific provider
    is chosen).

    Reads each provider's SUPPORTED_ENDPOINTS class attribute — a
    convention, not something enforced by AircraftInformationInterface
    itself, so a provider that doesn't declare it (None, or missing
    entirely) is treated as supporting every field SEARCH_FIELDS knows
    about.
    """
    if aircraft_interface is None:
        return []

    result = []
    for p in providers_container.aircraft_information_apis:
        supported = getattr(p, "SUPPORTED_ENDPOINTS", None)
        result.append(
            {
                "name": getattr(p, "SOURCE", "?"),
                "endpoints": sorted(supported) if supported else sorted(SEARCH_FIELDS),
            }
        )
    return result


async def list_credentials_for_ui() -> list[dict]:
    """
    Schema + safe display values for every provider that declares
    CREDENTIAL_FIELDS. Secret values are never returned; configured
    flags indicate whether a value is already stored locally.
    """
    from db.credentials_store import SECRET_KEYS, credentials_store

    providers_out = []
    for p in providers_container.aircraft_information_apis:
        # Instance attributes hold runtime state; field schema lives on the class.
        fields = getattr(type(p), "CREDENTIAL_FIELDS", None)
        if not fields:
            continue

        source = getattr(p, "SOURCE", "?")
        row = await credentials_store.get(source)

        values: dict[str, str] = {}
        configured: dict[str, bool] = {}
        for field in fields:
            key = field["key"]
            stored = getattr(row, key, None) if row else None
            configured[key] = bool(stored)
            # Non-secret columns can be prefilled in the form; secrets stay masked client-side.
            if key not in SECRET_KEYS and stored:
                values[key] = stored

        providers_out.append(
            {
                "source": source,
                "fields": list(fields),
                "values": values,
                "configured": configured,
            }
        )
    return providers_out
