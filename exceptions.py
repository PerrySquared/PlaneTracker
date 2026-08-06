class AircraftSourceError(Exception):
    """Base exception for any aircraft-data-source failure."""


class AircraftFetchError(AircraftSourceError):
    """Raised when a request to a source fails (network, timeout, bad status, bad body)."""


class AircraftParseError(AircraftSourceError):
    """Raised when a source's response can't be parsed into AircraftInformationBase."""
