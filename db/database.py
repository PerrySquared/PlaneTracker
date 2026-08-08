"""
Async SQLAlchemy engine/session setup for SQLite.

Uses the aiosqlite driver so DB calls await alongside the rest of the
app's asyncio stack (background_tasks.py's loops, FastAPI's async
routes) instead of blocking the event loop on every query.

Install: pip install aiosqlite --break-system-packages
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .models import Model

DB_PATH = Path(__file__).resolve().parent / "aircraft.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@event.listens_for(Engine, "connect")
def _enable_sqlite_pragmas(dbapi_connection, connection_record):
    """
    SQLite ships with both of these off by default:
      - foreign_keys=ON: without it, SQLite silently accepts an
        aircraft_state/favorite row referencing a hex that doesn't
        exist in aircraft — the ForeignKey() in models.py becomes
        decoration, not a constraint, unless this is set per connection.
      - journal_mode=WAL: lets background_tasks.py's writers (updating
        aircraft_state every poll cycle) and FastAPI's readers (search,
        favorites endpoints) hit the DB concurrently without blocking
        each other on every single request the way SQLite's default
        rollback-journal locking would.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


async def init_db() -> None:
    """Create tables if they don't exist yet. Call once at startup
    (e.g. in main.py's lifespan, alongside starting the background
    loops) — or switch to Alembic migrations once the schema needs to
    evolve without dropping data."""
    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)


@asynccontextmanager
async def get_session():
    async with SessionLocal() as session:
        yield session
