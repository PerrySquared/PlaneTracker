"""Configuration constants for the aircraft tracker server.

Static assets (index.html, globe.gl.min.js, world-geojson.js) live one
directory above this package — i.e. alongside main.js in gui/ —
matching where they sat next to the original flat server.py. That's a
fixed relationship to *this package's own location*, not a
project-root search: wherever the `server` package folder ends up,
its static assets are expected directly beside it.

Favorites are no longer a JSON file here — they're a table in the
`db` package at the project root (see favorites_store.py), found via
the same project-root search main.py already does for `api`/`container`.
"""

from pathlib import Path

BROADCAST_INTERVAL_SECONDS = 2.0  # how often to push a fresh batch to clients
# (cheap — reads from memory, no API calls)

SEARCH_FIELDS = {"hex", "callsign", "reg", "type", "squawk"}

MAX_FAVORITES = 25  # hard cap on how many planes can be favorited
FAVORITES_POLL_INTERVAL_SECONDS = 60  # separate, slower cadence for the extra
# per-favorite API hits this adds. Tune
# this and MAX_FAVORITES together —
# they set the worst-case extra API
# call rate: MAX_FAVORITES calls every
# FAVORITES_POLL_INTERVAL_SECONDS.
#
# This is also the trail resolution: one position_history row gets
# written per favorite per cycle (see background_tasks.py), so trails
# render with one point per FAVORITES_POLL_INTERVAL_SECONDS, not
# every BROADCAST_INTERVAL_SECONDS. The frontend's trail auto-refresh
# timer is kept in sync with this value — see TRAIL_REFRESH_MS in
# index.html.

FLIGHT_GAP_MINUTES = 30  # gap after which two points are considered
# different flights even if the callsign happens
# to repeat (see flight_segmentation.py)

MAX_HISTORY_POINTS = 3000  # cap on points returned per /history
# request. Keeps "full history" payloads bounded
# for long-tracked favorites; takes the most
# recent points if a track exceeds this, not the
# oldest, so long tracks still show their recent
# (most relevant) end rather than being cut off
# at the start.

STATIC_DIR = Path(__file__).resolve().parent.parent
INDEX_PATH = STATIC_DIR / "index.html"
GLOBE_JS_PATH = STATIC_DIR / "globe.gl.min.js"
GEOJSON_JS_PATH = STATIC_DIR / "world-geojson.js"
