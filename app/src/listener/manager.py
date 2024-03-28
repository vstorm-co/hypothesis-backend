from asyncio import Queue, QueueFull, Task, sleep
from functools import lru_cache
from logging import getLogger
from typing import Any, Optional

from src.chat.schemas import GlobalConnectMessage

logger = getLogger(__name__)


class ListenerManager:
    def __init__(self):
        # Every incoming websocket connection adds it own Queue to this list called
        # subscribers.
        self.subscribers: list[Queue] = []
        self.users_in_room: list[GlobalConnectMessage] = []
        # This will hold an asyncio task which will receives
        # messages and broadcasts them
        # to all subscribers.
        self.listener_task: Optional[Task] = None

    # TODO Need info about current user to skip they in the loop
    async def subscribe(self, q: Queue):
        # Every incoming websocket connection must create
        # a Queue and subscribe itself to
        # this class instance
        self.subscribers.append(q)
        for user_in_room in self.users_in_room:
            await self.receive_and_publish_message(user_in_room.model_dump(mode="json"))

    async def add_user_to_room(self, user_data: GlobalConnectMessage):
        self.users_in_room.append(user_data)

    async def remove_user_from_room(self, user_data: GlobalConnectMessage):
        self.users_in_room = [
            user
            for user in self.users_in_room
            if not user.is_equal_except_type(user_data)
        ]

    async def receive_and_publish_message(self, msg: Any):
        for q in self.subscribers:
            try:
                q.put_nowait(msg)
            except QueueFull:  # Queue is full
                logger.info("Queue for %s is full. Retrying in 1 second.", q)
                await sleep(1)  # Wait for 1 second before retrying
            except Exception as e:
                raise e


@lru_cache()
def get_listener_manager():
    return ListenerManager()


listener = get_listener_manager()
