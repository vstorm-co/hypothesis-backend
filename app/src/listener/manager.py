import asyncio
from asyncio import Queue, Task
from functools import lru_cache
from typing import Any

import websockets

from src.chat.schemas import ConnectMessage, GlobalConnectMessage
from src.config import settings


class ListenerManager:
    def __init__(self):
        # Every incoming websocket connection adds it own Queue to this list called
        # subscribers.
        self.subscribers: list[Queue] = []
        self.users_in_room: list[GlobalConnectMessage] = []
        # This will hold a asyncio task which will receives messages and broadcasts them
        # to all subscribers.
        self.listener_task: Task

    async def subscribe(self, q: Queue):
        # Every incoming websocket connection must create
        # a Queue and subscribe itself to
        # this class instance
        self.subscribers.append(q)
        for user_in_room in self.users_in_room:
            await self.receive_and_publish_message(user_in_room.model_dump())

    async def add_user_to_room(self, room_id: str, user_data: GlobalConnectMessage):
        self.users_in_room.append(user_data)

    async def remove_user_from_room(self, room_id: str, user_data: GlobalConnectMessage):
        for data in self.users_in_room:
            if data.is_equal_except_type(user_data):
                self.users_in_room.remove(data)

    async def start_listening(self):
        # Method that must be called on startup of application to start the listening
        # process of external messages.
        self.listener_task = asyncio.create_task(self._listener())

    async def _listener(self) -> None:
        # The method with the infinite listener.
        # It is started
        # (via start_listening()) on startup of app.
        async with websockets.connect(settings.GLOBAL_LISTENER_PATH) as websocket:
            async for message in websocket:
                for q in self.subscribers:
                    # important here: every websocket connection
                    # has its own Queue added to
                    # the list of subscribers. Here, we actually
                    # broadcast incoming messages
                    # to all open websocket connections.
                    await q.put(message)

    # TODO Check self.listener_task.result()
    async def stop_listening(self):
        # closing off the asyncio task when stopping the app. This method is called on
        # app shutdown
        # if self.listener_task.done():
        #     self.listener_task.result()
        # else:
        self.listener_task.cancel()

    async def receive_and_publish_message(self, msg: Any):
        for q in self.subscribers:
            try:
                q.put_nowait(str(msg))
            except Exception as e:
                raise e


@lru_cache()
def get_listener_manager():
    return ListenerManager()


listener = get_listener_manager()
