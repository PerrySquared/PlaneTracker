from http import HTTPStatus

import aiohttp
from aiohttp import ClientTimeout

from api.providers.base import AircraftInformationBase, AircraftInformationBaseResponse
from exceptions import AircraftFetchError

from .tokenmanager import TokenManager


class AircraftInformation(AircraftInformationBase):
    TIMEOUT = ClientTimeout(total=15)
    BASE_URL = "https://opensky-network.org/api"
    SOURCE = "opensky-network.org"

    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager

    def normalize_response(
        self, raw_response: dict
    ) -> list[AircraftInformationBaseResponse]:
        """Normalize data from a fetch into a list of AircraftInformationBase instances."""

        r_list = raw_response.get("states") or []
        return [self._parse_one_response(r) for r in r_list]

    async def fetch_data(
        self, values: list[str], path: str | None = "states/all"
    ) -> dict:
        """Fetch data from an OpenSky API endpoint

        The 'multiple' request endpoint is used for both single and multiple plane requests
        since OpenSky has no endpoints for searching by reg, callsign, etc. The method defaults
        to states/all every time as a precaution, explicit argument usage is preferrable.
        Howerver, the argument is still present for a possible scope increase.

        More: https://openskynetwork.github.io/opensky-api/rest.html
        """

        path = "states/all"
        url = f"{self.BASE_URL}/{path}?{'&'.join(f'icao24={value.lower()}' for value in values)}"

        return await self._request(url)

    async def _request(self, url: str) -> dict:
        """Send the request, raising AircraftFetchError on any transport-level failure."""

        try:
            async with (
                aiohttp.ClientSession(
                    timeout=self.TIMEOUT,
                    headers=await self.token_manager.headers(),
                ) as session,
                session.get(url) as response,
            ):
                if response.status != HTTPStatus.OK:
                    body = await response.text()
                    raise AircraftFetchError(
                        f"HTTP {response.status} from {self.SOURCE}: {body}"
                    )

                return await response.json()

        except TimeoutError:
            raise AircraftFetchError(f"{self.SOURCE} request timed out")
        except aiohttp.ClientError as e:
            raise AircraftFetchError(f"{self.SOURCE} connection error: {e}")

    def _parse_one_response(
        self, response_aircraft: dict
    ) -> AircraftInformationBaseResponse:
        """Normalize a single raw OpenSky state vector into an
        AircraftInformationBaseResponse.

        OpenSky returns aircraft state data as a two-dimensional ``states`` array,
        where each aircraft is represented by a positional state vector.

        OpenSky state vector fields:
            0  -> icao24
            1  -> callsign
            2  -> origin_country
            3  -> time_position
            4  -> last_contact
            5  -> longitude
            6  -> latitude
            7  -> baro_altitude (meters)
            8  -> on_ground
            9  -> velocity above ground (m/s)
            10 -> true_track (degrees)
            11 -> vertical_rate (m/s)
            12 -> sensors
            13 -> geo_altitude (meters)
            14 -> squawk
            15 -> spi
            16 -> position_source
            17 -> category

        Args:
            response_aircraft: A raw OpenSky API response containing a ``states``
                array. ``states`` is expected to contain a single state vector.

        Returns:
            The normalized AircraftInformationBaseResponse for the aircraft.

        Raises:
            ValidationError: If required fields are missing or fail type
                validation during model construction.
        """

        r = response_aircraft

        altitude_baro = "ground" if r[8] else r[7]

        return AircraftInformationBaseResponse(
            icao24=r[0],
            registration=None,
            aircraft_type=None,
            flags=None,
            callsign=r[1],
            squawk=r[14],
            latitude=r[6],
            longitude=r[5],
            altitude_baro=altitude_baro,
            rate_baro=r[11],
            ground_speed=None,
            track=r[10],
            last_seen_position=None,
            source=self.SOURCE,
        )
