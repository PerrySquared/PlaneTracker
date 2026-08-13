import datetime as dt
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv()

TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
CLIENT_ID = os.getenv("OPENSKY_CLIENT_ID")
CLIENT_SECRET = os.getenv("OPENSKY_CLIENT_SECRET")

# How many seconds before expiry to proactively refresh the token.
TOKEN_REFRESH_MARGIN = 120


class TokenManager:
    def __init__(self):
        self.token = None
        self.expires_at = None

    def get_token(self):
        """Return a valid access token, refreshing automatically if needed."""

        if self.token and self.expires_at and dt.datetime.now(dt.UTC) < self.expires_at:
            return self.token
        return self._refresh()

    async def _request_token(self):
        """Fetch the acces token from the auth server."""

        async with aiohttp.ClientSession() as session:
            r = await session.post(
                TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
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

    def headers(self):
        """Return request headers with a valid Bearer token."""

        return {"Authorization": f"Bearer {self.get_token()}"}


# Create a single shared instance for your script.
# tokens = TokenManager()

# Use it for any API call - the token is refreshed automatically.
# response = requests.get(
#     "https://opensky-network.org/api/states/all",
#     headers=tokens.headers(),
# )
# print(response.json())
