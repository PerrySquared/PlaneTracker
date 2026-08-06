from providers import airplaneslive, base

from exceptions import AircraftFetchError, AircraftSourceError

airplaneslive_instance = airplaneslive.AircraftInformation()
logged_in = False
if logged_in:
    opensky_instance = 0


async def fetch_normalized_flight_data(
    search: list[str], api_endpoint_select: str | None
) -> list[base.AircraftInformationBase]:
    """Fetching interface for providers with automatic fallback."""
    providers = [airplaneslive_instance, opensky_instance]  # priority order

    last_error = None
    for provider in providers:
        try:
            raw_response = await provider.fetch_data(search, api_endpoint_select)
            return provider.normalize_response(raw_response)
        except AircraftSourceError as e:
            last_error = e
            continue  # try next provider

    raise AircraftFetchError(f"All providers failed. Last error: {last_error}")
