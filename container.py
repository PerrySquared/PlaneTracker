from api.providers.airplaneslive import parser as airplaneslive
from api.providers.opensky import parser as opensky
from api.providers.opensky.tokenmanager import TokenManager as opensky_tm


class Container:
    def __init__(self):
        self.aircraft_information_apis = [
            airplaneslive.AircraftInformation(),
            opensky.AircraftInformation(opensky_tm()),
        ]
