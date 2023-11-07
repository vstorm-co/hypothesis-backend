import asyncio
from asyncio import Queue, Task
from typing import Any

import websockets


class ListenerManager:
    def __init__(self):
        # Every incoming websocket connection adds it own Queue to this list called
        # subscribers.
        self.subscribers: list[Queue] = []
        # This will hold a asyncio task which will receives messages and broadcasts them
        # to all subscribers.
        self.listener_task: Task

    async def subscribe(self, q: Queue):
        # Every incoming websocket connection must create
        # a Queue and subscribe itself to
        # this class instance
        self.subscribers.append(q)

    async def start_listening(self):
        # Method that must be called on startup of application to start the listening
        # process of external messages.
        self.listener_task = asyncio.create_task(self._listener())

    async def _listener(self) -> None:
        # The method with the infinite listener. In this example,
        # it listens to a websocket
        # as it was the fastest way for me to mimic the
        # 'infinite generator' in issue 5015
        # but this can be anything. It is started
        # (via start_listening()) on startup of app.
        async with websockets.connect("ws://localhost:8001") as websocket:
            async for message in websocket:
                for q in self.subscribers:
                    # important here: every websocket connection
                    # has its own Queue added to
                    # the list of subscribers. Here, we actually
                    # broadcast incoming messages
                    # to all open websocket connections.
                    await q.put(message)

    async def stop_listening(self):
        # closing off the asyncio task when stopping the app. This method is called on
        # app shutdown
        if self.listener_task.done():
            self.listener_task.result()
        else:
            self.listener_task.cancel()

    async def receive_and_publish_message(self, msg: Any):
        for q in self.subscribers:
            try:
                q.put_nowait(str(msg))
            except Exception as e:
                raise e
