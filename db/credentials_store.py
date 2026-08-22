"""
Credentials for API providers — backed by the `credentials` table in
db/models.py. Used by provider token managers and the settings
UI via gui/server/routes/credentials.py.
"""

from __future__ import annotations

from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from db.database import get_session
from db.models import Credential

# Columns that must not be echoed back to the UI after save.
SECRET_KEYS = frozenset({"client_secret", "password", "api_key"})

CREDENTIAL_COLUMNS = frozenset(
    {"client_id", "client_secret", "login", "password", "api_key"}
)


class CredentialsStore:
    async def get(self, source: str) -> Credential | None:
        """
        Load the full credential row for a provider `source` key (matches
        AircraftInformationBase.SOURCE, e.g. "opensky-network.org").

        Returns None when nothing is stored yet. Callers that need secrets
        (TokenManager) use this directly; the settings UI goes through
        list_credentials_for_ui() instead, which strips secret columns.
        """
        async with get_session() as session:
            return await session.get(Credential, source)

    async def upsert(self, source: str, payload: dict) -> None:
        """
        Insert or update the credential row for `source`.

        `payload` may contain any subset of CREDENTIAL_COLUMNS. Keys not
        present are left unchanged on update. An empty string for a secret
        column means "keep the value already in the DB" rather than wipe
        it — that lets the UI save non-secret fields without resending
        passwords the form never echoed back.
        """
        existing = await self.get(source)
        values: dict[str, str | None] = {"source": source}

        for key in CREDENTIAL_COLUMNS:
            if key not in payload:
                continue
            raw = payload[key]
            if raw is None:
                continue
            stripped = raw.strip() if isinstance(raw, str) else raw
            if key in SECRET_KEYS and stripped == "" and existing:
                values[key] = getattr(existing, key)
            else:
                values[key] = stripped or None

        # Carry forward any columns the caller didn't mention this time.
        if existing:
            for key in CREDENTIAL_COLUMNS:
                if key not in values and getattr(existing, key) is not None:
                    values[key] = getattr(existing, key)

        async with get_session() as session:
            stmt = sqlite_insert(Credential).values(**values)
            update_cols = {k: v for k, v in values.items() if k != "source"}
            stmt = stmt.on_conflict_do_update(index_elements=["source"], set_=update_cols)
            await session.execute(stmt)

    async def delete(self, source: str) -> None:
        """
        Remove all stored credentials for a provider. No-op if the row
        does not exist. Routes call this from the settings UI "Clear"
        action and invalidate the provider's token cache afterward.
        """
        async with get_session() as session:
            row = await session.get(Credential, source)
            if row:
                await session.delete(row)


credentials_store = CredentialsStore()
