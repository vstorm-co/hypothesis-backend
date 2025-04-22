import asyncio
import json
import logging
from datetime import timedelta
from typing import Optional, Callable, Awaitable

from redis import asyncio as aioredis
from redis.asyncio import Redis

from src.config import settings
from src.constants import Environment
from src.models import ORJSONModel

logger = logging.getLogger(__name__)

redis_client: Redis | None = None


class RedisData(ORJSONModel):
    key: bytes | str
    value: bytes | str
    ttl: Optional[int | timedelta]


async def set_redis_key(redis_data: RedisData, *, is_transaction: bool = False) -> None:
    if not redis_client:
        return None

    async with redis_client.pipeline(transaction=is_transaction) as pipe:
        await pipe.set(redis_data.key, redis_data.value)
        if redis_data.ttl:
            await pipe.expire(redis_data.key, redis_data.ttl)

        await pipe.execute()


async def get_by_key(key: str) -> Optional[str]:
    if not redis_client:
        return None

    return await redis_client.get(key)


async def delete_by_key(key: str) -> Optional[int]:
    if not redis_client:
        return None

    return await redis_client.delete(key)



class RedisPubSubManager:
    def __init__(self):
        self.redis = redis.Redis()
        self.subscribed_channels: set[str] = set()
        self.channel_callbacks: dict[str, Callable[[str, dict], asyncio.Future]] = {}
        self.listener_task: asyncio.Task | None = None

    async def subscribe(self, channel: str, callback: Callable[[str, dict], asyncio.Future]):
        if channel in self.subscribed_channels:
            return

        self.subscribed_channels.add(channel)
        self.channel_callbacks[channel] = callback

        if not self.listener_task or self.listener_task.done():
            self.listener_task = asyncio.create_task(self._listen())

    async def unsubscribe(self, channel: str):
        if channel in self.subscribed_channels:
            self.subscribed_channels.remove(channel)
            self.channel_callbacks.pop(channel, None)
            await self.redis.unsubscribe(channel)

    async def publish(self, channel: str, message: dict):
        await self.redis.publish(channel, json.dumps(message))

    async def _listen(self):
        while True:
            try:
                pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
                if self.subscribed_channels:
                    await pubsub.subscribe(*self.subscribed_channels)

                async for message in pubsub.listen():
                    if message is None:
                        continue
                    if message["type"] != "message":
                        continue

                    channel = message["channel"].decode()
                    data = json.loads(message["data"])

                    callback = self.channel_callbacks.get(channel)
                    if callback:
                        await callback(channel, data)
            except Exception as e:
                logger.error(f"Redis listen error: {e}")
                await asyncio.sleep(2)  # Retry on failure


pub_sub_manager = RedisPubSubManager()
