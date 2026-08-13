from api.providers.airplaneslive import parser as airplaneslive


class Container:
    def __init__(self):
        self.aircraft_information_apis = [
            airplaneslive.AircraftInformation(),
        ]
