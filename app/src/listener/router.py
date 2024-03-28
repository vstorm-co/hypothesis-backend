import asyncio
import logging

from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect

from src.listener.manager import listener
from src.listener.schemas import WSEventMessage

router = APIRouter()

logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    await listener.subscribe(q=q)
    try:
        while True:
            data = await q.get()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        pass


@router.get("/test")
async def test():
    await listener.receive_and_publish_message(
        WSEventMessage(type="test").model_dump(mode="json")
    )
    return {"status": "ok"}
