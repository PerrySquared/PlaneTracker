"""
Favorites — backed by the `favorites` table in db/models.py instead of
a JSON file, so they live alongside aircraft/aircraft_state in one
database rather than a separate file that could drift out of sync.

All methods are now coroutines (the old JSON-backed version was
synchronous) — callers need to `await` them; see routes/favorites.py,
routes/search.py, and background_tasks.py.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from db.database import SessionLocal
from db.models import Aircraft, Favorite

log = logging.getLogger("aircraft-server")


class FavoritesStore:
    def __init__(self, max_favorites: int):
        self.max_favorites = max_favorites

    async def list(self) -> list[str]:
        async with SessionLocal() as session:
            result = await session.execute(select(Favorite.hex))
            return [row[0] for row in result.all()]

    async def add(self, hex_code: str) -> bool:
        hex_code = hex_code.lower()
        async with SessionLocal() as session:
            if await session.get(Favorite, hex_code):
                return True

            # session.scalar()'s return type is Optional[int] even for
            # COUNT(*), which never actually returns NULL — the `or 0`
            # satisfies the type checker without changing behavior.
            count = await session.scalar(select(func.count()).select_from(Favorite)) or 0
            if count >= self.max_favorites:
                return False

            # favorites.hex has a FK to aircraft.hex — make sure a row
            # exists even if the aircraft hasn't actually broadcast yet,
            # matching the old JSON store's behavior of allowing any hex
            # code to be favorited up front.
            aircraft_stmt = sqlite_insert(Aircraft).values(hex=hex_code)
            aircraft_stmt = aircraft_stmt.on_conflict_do_nothing(index_elements=["hex"])
            await session.execute(aircraft_stmt)

            session.add(Favorite(hex=hex_code))
            try:
                await session.commit()
            except Exception:
                log.exception("Could not add favorite %s", hex_code)
                await session.rollback()
                return False
            return True

    async def remove(self, hex_code: str) -> None:
        hex_code = hex_code.lower()
        async with SessionLocal() as session:
            fav = await session.get(Favorite, hex_code)
            if fav:
                await session.delete(fav)
                await session.commit()
