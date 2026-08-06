import asyncio
from http import HTTPStatus

import aiohttp
from aiohttp import ClientTimeout

from api.providers.base import AircraftInformationBase
from exceptions import AircraftFetchError


class AircraftInformation:
    TIMEOUT = ClientTimeout(total=10)
    BASE_URL = "https://api.airplanes.live/v2"
    SOURCE = "airplanes.live"

    def normalize_response(self, response: dict) -> list[AircraftInformationBase]:
        """Normalize data from a fetch into a list of AircraftInformationBase instances."""

        r_list = response.get("ac", [])  # access the AirCrafts part of a response

        return [self._parse_one_response(r) for r in r_list]

    async def _request(self, url: str) -> aiohttp.ClientResponse:
        """Send the request, raising AircraftFetchError on any transport-level failure."""

        try:
            async with aiohttp.ClientSession(timeout=self.TIMEOUT) as session:
                return await session.get(url)

        except TimeoutError:
            raise AircraftFetchError(f"{self.SOURCE} request timed out")
        except aiohttp.ClientError as e:
            raise AircraftFetchError(f"{self.SOURCE} connection error: {e}")

    async def _get_json(self, response: aiohttp.ClientResponse) -> dict:
        """Validate status and parse the body, raising AircraftFetchError on failure."""

        if response.status != HTTPStatus.OK:
            raise AircraftFetchError(f"HTTP {response.status} from {self.SOURCE}")
        try:
            return await response.json()

        except aiohttp.ContentTypeError:
            raise AircraftFetchError(f"{self.SOURCE} returned non-JSON response")

    async def fetch_data(self, path: str, values: list[str]) -> dict:
        """Fetch data from a selection of airplaneslive API endpoints.

        Requires the desired endpoint part of the path (hex, callsign, reg...)
        and a list of search strings (a list with a singular element is acceptable)

        Available endpoints:
        /hex/[hex]
        /callsign/[callsign]
        /reg/[reg]
        /type/[type]
        /squawk/[squawk]

        More: https://airplanes.live/api-guide/
        """

        url = f"{self.BASE_URL}/{path}/{','.join(values)}"
        response = await self._request(url)
        return await self._get_json(response)

    def _parse_one_response(self, response_plane: dict) -> AircraftInformationBase:
        """Normalize a single raw aircraft record from the airplanes.live API into
        an AircraftInformationBase.

        Maps the API's raw field names to canonical model fields:
        hex       -> icao24              24-bit ICAO Mode S address, primary key
        r         -> registration        tail number, e.g. "N12345"
        t         -> aircraft_type       ICAO type code, e.g. "C25A"
        dbFlags   -> flags               bitfield: military=1, interesting=2, PIA=4, LADD=8
        flight    -> callsign            8-char field, often space-padded
        lat/lon   -> latitude/longitude  falls back to lastPosition if stale (>60s)
        alt_baro  -> altitude_baro       feet, or literal string "ground"
        baro_rate -> rate_baro           ft/min, negative = descending
        gs        -> ground_speed        knots
        track     -> track               true track over ground, degrees (0-359)

        Args:
            response_plane: A single element of the API response's `ac` array.

        Returns:
            The normalized AircraftInformationBase for this aircraft.

        Raises:
            ValidationError: If required fields are missing or fail type
                validation during model construction.
        """

        r = response_plane

        lat = r.get("lat")
        lon = r.get("lon")
        last_position = r.get("lastPosition")

        if lat is None and last_position:
            lat = last_position.get("lat")
            lon = last_position.get("lon")

        return AircraftInformationBase(
            icao24=r.get("hex"),
            registration=r.get("r"),
            aircraft_type=r.get("t"),
            flags=r.get("dbFlags"),
            callsign=r.get("flight"),
            latitude=lat,
            longitude=lon,
            altitude_baro=r.get("alt_baro"),
            rate_baro=r.get("baro_rate"),
            ground_speed=r.get("gs"),
            track=r.get("track"),
            last_seen_position=last_position,
            source=self.SOURCE,
        )


async def main():
    ICAO24 = "AC5CD7"
    pi = AircraftInformation()
    pd = await pi.fetch_data("hex", [ICAO24])
    r = pi.normalize_response(pd)
    print(r)


if __name__ == "__main__":
    asyncio.run(main())
