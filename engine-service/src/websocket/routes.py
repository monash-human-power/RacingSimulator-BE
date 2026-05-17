from .connectionManager import ConnectionManager
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set

manager = ConnectionManager()

router = APIRouter()

@router.websocket("/ws/engine")
async def websocket_engine_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Broadcast engine output to all connected clients
            await manager.broadcast({"type": "engine_output", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.post("/broadcast/engine")
async def broadcast_engine_output(engine_data: dict):
    """Broadcast engine output to all connected WebSocket clients"""
    await manager.broadcast({"type": "engine_output", "data": engine_data})
    return {"status": "broadcasted"}