"""
Aircraft tracker WebSocket server — entrypoint.

Bridges AircraftInformationInterface to the globe.gl frontend in
index.html. There's one required integration point (aircraft_interface,
in aircraft_service.py) and one optional one (get_current_aircraft, also
in aircraft_service.py — see its docstring). Everything else (connection
handling, search, favorites, broadcasting, serialization) is already
wired up against the real AircraftInformationBaseResponse schema.

Run (from the directory that contains this "server" package, i.e. the
project root):
    pip install fastapi uvicorn aiosqlite --break-system-packages
    python -m server.main

Then open index.html directly in a browser, or visit http://localhost:8000/
(this server also serves index.html as a convenience — see routes/static.py).
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI


def _find_project_root(start: Path) -> Path:
    """
    Walk upward from this file looking for the directory that has
    `container.py` and an `api/` package alongside it — i.e. the
    project root that `aircraft_service.py`'s `from api...` / `from
    container...` imports expect on sys.path.

    Searching (rather than a hardcoded number of `.parent` hops) means
    this keeps working if `server/` ever moves — e.g. it currently
    sits inside `gui/` for Electron packaging, one level deeper than
    when it was a flat `server.py` next to `main.js`. Falls back to
    two levels up (this file's old assumption) if nothing is found,
    so it still errors in the same recognizable way rather than
    silently picking the wrong directory.
    """
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "container.py").exists() and (candidate / "api").is_dir():
            return candidate
    return start.resolve().parent.parent


# Keeps `from api...` / `from container...` / `from db...` imports
# resolvable regardless of how deep this package is nested.
sys.path.insert(0, str(_find_project_root(Path(__file__).parent)))

from db.database import init_db

from .background_tasks import broadcast_loop, favorites_poll_loop
from .routes import credentials, favorites, history, search, static, websocket

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("aircraft-server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()  # create tables if they don't exist yet
    asyncio.create_task(broadcast_loop())
    asyncio.create_task(favorites_poll_loop())
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(favorites.router)
app.include_router(credentials.router)
app.include_router(search.router)
app.include_router(history.router)
app.include_router(websocket.router)
app.include_router(static.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
