"""
Shared, process-wide instances. Kept in one place — rather than, say,
constructing `favorites` inside main.py — so routes/*.py and
background_tasks.py can both import them without circular-importing
main.py itself.
"""

import asyncio

from .config import MAX_FAVORITES
from .connection_manager import ConnectionManager
from .favorites_store import FavoritesStore

manager = ConnectionManager()
favorites = FavoritesStore(MAX_FAVORITES)

# Cache of the favorites' latest polled data; broadcast_loop just reads it
# (cheap, no API calls) — favorites_poll_loop (background_tasks.py) is the
# only thing that actually hits search_aircraft() for them, on its own
# slower cadence.
favorite_cache: dict[str, dict] = {}
favorite_cache_lock = asyncio.Lock()
