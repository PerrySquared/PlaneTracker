"""Live aircraft feed over WebSocket."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..state import manager

router = APIRouter()


@router.websocket("/ws/aircraft")
async def aircraft_ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # The client doesn't send anything meaningful; this just lets us
            # detect disconnects promptly instead of waiting on a dead socket.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
