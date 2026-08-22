import datetime as dt
from collections.abc import Awaitable, Callable

import aiohttp

from db.models import Credential
from exceptions import AircraftFetchError

TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"

# How many seconds before expiry to proactively refresh the token.
TOKEN_REFRESH_MARGIN = 120


class TokenManager:
    def __init__(
        self,
        source: str,
        get_credentials: Callable[[str], Awaitable[Credential | None]],
    ):
        self.source = source
        self._get_credentials = get_credentials
        self.token = None
        self.expires_at = None

    def invalidate(self) -> None:
        self.token = None
        self.expires_at = None

    async def get_token(self):
        """Return a valid access token, refreshing automatically if needed."""

        if self.token and self.expires_at and dt.datetime.now(dt.UTC) < self.expires_at:
            return self.token
        return await self._refresh()

    async def _request_token(self):
        """Fetch the access token from the auth server."""

        creds = await self._get_credentials(self.source)
        if not creds or not creds.client_id or not creds.client_secret:
            raise AircraftFetchError(f"{self.source} credentials not configured")

        async with aiohttp.ClientSession() as session:
            r = await session.post(
                TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                },
            )
            r.raise_for_status()
            return r

    async def _parse_token(self, token: aiohttp.ClientResponse):
        """Parse the access token."""

        data = await token.json()
        self.token = data["access_token"]
        expires_in = data.get("expires_in", 1800)
        self.expires_at = dt.datetime.now(dt.UTC) + dt.timedelta(
            seconds=expires_in - TOKEN_REFRESH_MARGIN
        )
        return self.token

    async def _refresh(self):
        """Refresh the access token."""

        response = await self._request_token()
        return await self._parse_token(response)

    async def headers(self):
        """Return request headers with a valid Bearer token."""

        return {"Authorization": f"Bearer {await self.get_token()}"}
