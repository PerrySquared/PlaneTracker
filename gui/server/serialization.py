"""
Convert one AircraftInformationBaseResponse (see api/providers/base.py)
into the plain JSON shape index.html expects.
"""

import logging

from api.providers.base import AircraftInformationBaseResponse

log = logging.getLogger("aircraft-server")


def serialize_aircraft(ac: AircraftInformationBaseResponse) -> dict:
    return {
        "icao24": ac.icao24,
        "registration": ac.registration,
        "callsign": ac.callsign.strip() if ac.callsign is not None else None,
        "aircraft_type": ac.aircraft_type,
        "squawk": ac.squawk,
        "latitude": ac.latitude,
        "longitude": ac.longitude,
        "altitude_baro": _normalize_altitude(ac.altitude_baro),
        "rate_baro": ac.rate_baro,
        "ground_speed": ac.ground_speed,
        "track": ac.track,
    }


def _normalize_altitude(alt):
    """
    altitude_baro is typed `int | str | None` on AircraftInformationBaseResponse
    — ADS-B sources commonly report the literal string "ground" instead of a
    numeric altitude for aircraft on the ground. Normalize that to 0 here so
    the frontend (which expects a number) doesn't need to special-case it —
    0 also happens to land in the same "on ground" grey band the altitude
    color scale already uses for null/unknown.
    """
    if alt is None:
        return None
    if isinstance(alt, str):
        if alt.strip().lower() == "ground":
            return 0
        try:
            return float(alt)
        except ValueError:
            log.warning("Unrecognized altitude_baro string value: %r", alt)
            return None
    return alt
