from pydantic import BaseModel


class AircraftInformationBase(BaseModel):
    """Canonical internal representation — no knowledge of any API's field names."""

    icao24: str | None = None
    registration: str | None = None
    aircraft_type: str | None = None
    flags: int | None = None
    callsign: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude_baro: int | str | None = None
    rate_baro: float | None = None
    ground_speed: float | None = None
    track: float | None = None
    last_seen_position: dict | None = None
    source: str = ""
