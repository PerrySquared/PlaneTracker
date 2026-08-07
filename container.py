from api import providers


class Container:
    def __init__(self):
        self.aircraft_information_apis = [
            providers.airplaneslive.AircraftInformation(),
        ]
