from api.providers.base import AircraftInformationBase  # noqa

from api.providers.airplaneslive import parser as airplaneslive
from api.providers.opensky import parser as opensky
from api.providers.opensky.tokenmanager import TokenManager as opensky_tm


class ProvidersContainer:
    def __init__(self):
        self.airplaneslive = airplaneslive.AircraftInformation()
        self.opensky = opensky.AircraftInformation(opensky_tm())

        self.aircraft_information_apis: list[AircraftInformationBase] = [
            self.airplaneslive,
            self.opensky,
        ]

        self.aircraft_information_by_name: dict[str, AircraftInformationBase] = {
            "airplanes.live": self.airplaneslive,
            "opensky-network.org": self.opensky,
        }

    def get_provider_object_from_string(self, provider: str | None):
        """Return provider's AircraftInformationBase-based object from query string"""
        if provider is None:
            return None
        try:
            return self.aircraft_information_by_name[provider]
        except KeyError:
            raise ValueError(f"No provider with {provider} name found")


providers_container = ProvidersContainer()
