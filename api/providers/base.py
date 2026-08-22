from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel


class AircraftInformationBaseResponse(BaseModel):
    """Canonical internal representation — no knowledge of any API's field names."""

    icao24: str | None = None
    registration: str | None = None
    aircraft_type: str | None = None
    flags: int | None = None
    callsign: str | None = None
    squawk: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude_baro: float | str | None = None
    rate_baro: float | None = None
    ground_speed: float | None = None
    track: float | None = None
    last_seen_position: dict | None = None
    source: str = ""


class AircraftInformationBase(ABC):
    BASE_URL: str
    SOURCE: str
    # None means every endpoint used by the UI is available
    SUPPORTED_ENDPOINTS: ClassVar[tuple[str, ...] | None]
    # None means the provider needs no API credentials
    CREDENTIAL_FIELDS: ClassVar[tuple[dict, ...] | None] = None

    def __init__(self, token_manager):
        self.token_manager = token_manager

    @abstractmethod
    async def fetch_data(self, values: list[str], path: str | None) -> dict: ...

    @abstractmethod
    def normalize_response(
        self, raw_response: dict
    ) -> list[AircraftInformationBaseResponse]: ...
