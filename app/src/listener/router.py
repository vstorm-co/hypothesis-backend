import asyncio
import logging

from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect

from src.listener.constants import listener_room_name
from src.listener.manager import ws_manager

router = APIRouter()

logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await ws_manager.add_user_to_room(room_id=listener_room_name, websocket=websocket)
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    try:
        while True:
            data = await q.get()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        await ws_manager.remove_user_from_room(
            room_id=listener_room_name, websocket=websocket
        )
