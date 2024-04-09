import asyncio
import logging

from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect

from src.chat.test_manager import test_manager
from src.listener.manager import listener
from src.listener.schemas import WSEventMessage
from src.redis import listener_room_name

router = APIRouter()

logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await test_manager.add_user_to_room(room_id=listener_room_name, websocket=websocket)
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    await listener.subscribe(q=q)
    try:
        while True:
            data = await q.get()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        await test_manager.remove_user_from_room(
            room_id=listener_room_name, websocket=websocket
        )


@router.get("/test")
async def test():
    await listener.receive_and_publish_message(
        WSEventMessage(type="test").model_dump(mode="json")
    )
    return {"status": "ok"}
