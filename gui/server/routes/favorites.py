"""Favorites CRUD endpoints."""

from fastapi import APIRouter, HTTPException

from ..state import favorites

router = APIRouter(tags=["favorites"])


@router.get("/favorites")
async def list_favorites():
    return {"favorites": await favorites.list(), "max": favorites.max_favorites}


@router.post("/favorites/{hex_code}")
async def add_favorite(hex_code: str):
    if not await favorites.add(hex_code):
        raise HTTPException(
            status_code=400,
            detail=f"Favorites limit reached ({favorites.max_favorites}).",
        )
    return {"favorites": await favorites.list(), "max": favorites.max_favorites}


@router.delete("/favorites/{hex_code}")
async def remove_favorite(hex_code: str):
    await favorites.remove(hex_code)
    return {"favorites": await favorites.list(), "max": favorites.max_favorites}
