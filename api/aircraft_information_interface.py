from exceptions import AircraftFetchError, AircraftSourceError

from .providers import base


class AircraftInformationInterface:
    def __init__(self, providers):
        self.providers = providers

    async def fetch_normalized_flight_data(
        self, search: list[str], api_endpoint_select: str | None = None
    ) -> list[base.AircraftInformationBaseResponse]:
        """Fetching interface for providers with automatic fallback."""

        last_error = None
        for provider in self.providers:
            try:
                print(f"Searching for {search} at {api_endpoint_select} with {provider}")
                raw_response = await provider.fetch_data(search, api_endpoint_select)
                return provider.normalize_response(raw_response)
            except AircraftSourceError as e:
                last_error = e
                print(f"Soft Fail: {last_error}")
                continue  # try next provider

        raise AircraftFetchError(f"All providers failed. Last error: {last_error}")
