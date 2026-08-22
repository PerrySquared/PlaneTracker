"""
Convenience: serve index.html (and its assets) from the same server, so
the app is reachable at http://localhost:8000/ instead of opening the
file separately. Safe to delete this router if the frontend is served
some other way — the WebSocket endpoint doesn't depend on it.
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..config import (
    AIRPORTS_JS_PATH,
    APPLE_TOUCH_ICON_PATH,
    FAVICON_32_PATH,
    FAVICON_ICO_PATH,
    GEOJSON_JS_PATH,
    GLOBE_JS_PATH,
    INDEX_PATH,
)

router = APIRouter(include_in_schema=False)


@router.get("/")
async def index():
    if INDEX_PATH.exists():
        return FileResponse(INDEX_PATH)
    return {"detail": "index.html not found next to the server package"}


@router.get("/globe.gl.min.js")
async def globe_js():
    return FileResponse(GLOBE_JS_PATH, media_type="application/javascript")


@router.get("/world-geojson.js")
async def world_geojson_js():
    return FileResponse(GEOJSON_JS_PATH, media_type="application/javascript")


@router.get("/airports.js")
async def airports_js():
    return FileResponse(AIRPORTS_JS_PATH, media_type="application/javascript")


@router.get("/favicon-32.png")
async def favicon_32():
    return FileResponse(FAVICON_32_PATH, media_type="image/png")


@router.get("/favicon.ico")
async def favicon_ico():
    return FileResponse(FAVICON_ICO_PATH, media_type="image/x-icon")


@router.get("/apple-touch-icon.png")
async def apple_touch_icon():
    return FileResponse(APPLE_TOUCH_ICON_PATH, media_type="image/png")
