"""WebSocket connection tracking + broadcast."""

import logging

from fastapi import WebSocket

log = logging.getLogger("aircraft-server")


class ConnectionManager:
    def __init__(self):
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
        log.info("Client connected (%d total)", len(self.active))

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
        log.info("Client disconnected (%d total)", len(self.active))

    async def broadcast(self, message: str):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:  # noqa
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
