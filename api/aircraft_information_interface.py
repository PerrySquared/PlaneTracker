from exceptions import AircraftFetchError, AircraftSourceError

from .providers import base
from .providers.base import AircraftInformationBase


class AircraftInformationInterface:
    def __init__(self, providers):
        self.providers = providers

    async def fetch_normalized_flight_data(
        self,
        search: list[str],
        api_endpoint_select: str | None = None,
        provider: AircraftInformationBase | None = None,
    ) -> list[base.AircraftInformationBaseResponse]:
        """Fetching interface for providers with automatic fallback."""

        providers = [provider] if provider else self.providers

        last_error = None
        for p in providers:
            try:
                print(f"Searching for {search} at {api_endpoint_select} with {p}")
                raw_response = await p.fetch_data(search, api_endpoint_select)
                return p.normalize_response(raw_response)
            except AircraftSourceError as e:
                last_error = e
                print(f"Soft Fail: {last_error}")
                continue  # try next provider

        raise AircraftFetchError(f"All providers failed. Last error: {last_error}")
