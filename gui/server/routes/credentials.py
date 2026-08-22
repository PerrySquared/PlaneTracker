"""Credentials CRUD for API providers that require local keys."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from container import providers_container
from db.credentials_store import CREDENTIAL_COLUMNS, SECRET_KEYS, credentials_store

from ..aircraft_service import list_credentials_for_ui

router = APIRouter(tags=["credentials"])


class CredentialUpdate(BaseModel):
    client_id: str | None = None
    client_secret: str | None = None
    login: str | None = None
    password: str | None = None
    api_key: str | None = None


def _provider_fields(source: str) -> tuple[dict, ...]:
    try:
        provider = providers_container.aircraft_information_by_name[source]
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown provider '{source}'.")
    fields = getattr(type(provider), "CREDENTIAL_FIELDS", None)
    if not fields:
        raise HTTPException(
            status_code=404, detail=f"Provider '{source}' does not use credentials."
        )
    return fields


def _invalidate_token(source: str) -> None:
    provider = providers_container.aircraft_information_by_name[source]
    token_manager = getattr(provider, "token_manager", None)
    if token_manager and hasattr(token_manager, "invalidate"):
        token_manager.invalidate()


@router.get("/credentials")
async def get_credentials():
    return {"providers": await list_credentials_for_ui()}


@router.put("/credentials/{source}")
async def update_credentials(source: str, body: CredentialUpdate):
    fields = _provider_fields(source)
    payload = body.model_dump(exclude_unset=True)

    unknown = set(payload) - CREDENTIAL_COLUMNS
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown credential field(s): {sorted(unknown)}",
        )

    allowed_keys = {f["key"] for f in fields}
    for key in payload:
        if key not in allowed_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Field '{key}' is not used by provider '{source}'.",
            )

    existing = await credentials_store.get(source)
    # Every field declared for a provider is required; secrets may be omitted
    # when a value is already stored locally (merge on upsert).
    for field in fields:
        key = field["key"]
        value = payload.get(key)
        if value is not None and str(value).strip():
            continue
        if key in SECRET_KEYS and existing and getattr(existing, key):
            continue
        raise HTTPException(
            status_code=400,
            detail=f"Missing required field '{key}' for provider '{source}'.",
        )

    await credentials_store.upsert(source, payload)
    _invalidate_token(source)
    return {"ok": True}


@router.delete("/credentials/{source}")
async def delete_credentials(source: str):
    _provider_fields(source)
    await credentials_store.delete(source)
    _invalidate_token(source)
    return {"ok": True}
