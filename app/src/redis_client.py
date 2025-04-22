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
        self.redis: Redis | None = None
        self.pubsub = None
        self.listeners: dict[str, Callable[[str, dict], Awaitable[None]]] = {}

    async def _get_connection(self) -> Redis:
        if not self.redis:
            self.redis = aioredis.Redis.from_url(
                settings.REDIS_URL.unicode_string(),
                decode_responses=True,
            )
        return self.redis

    async def connect(self):
        self.redis = await self._get_connection()
        self.pubsub = self.redis.pubsub()
        logger.info("Connected to Redis and initialized PubSub.")

    async def disconnect(self):
        if self.pubsub:
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()

    async def publish(self, room_id: str, message: dict | str):
        if settings.ENVIRONMENT == Environment.DEBUG:
            return
        await self._get_connection()
        if isinstance(message, dict):
            message = json.dumps(message)
        await self.redis.publish(room_id, message)

    async def subscribe(self, room_id: str, callback: Callable[[str, dict], Awaitable[None]]):
        await self._get_connection()
        if not self.pubsub:
            self.pubsub = self.redis.pubsub()
            asyncio.create_task(self._listen())

        await self.pubsub.subscribe(room_id)
        self.listeners[room_id] = callback
        logger.info(f"Subscribed to room {room_id}")

    async def unsubscribe(self, room_id: str):
        if self.pubsub:
            await self.pubsub.unsubscribe(room_id)
            self.listeners.pop(room_id, None)
            logger.info(f"Unsubscribed from room {room_id}")

    async def _listen(self):
        logger.info("Started Redis PubSub listener.")
        while True:
            try:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not message:
                    await asyncio.sleep(0.01)
                    continue

                room_id = message["channel"]
                data = json.loads(message["data"])
                callback = self.listeners.get(room_id)
                if callback:
                    await callback(room_id, data)

            except Exception as e:
                logger.exception("Redis PubSub listener error: %s", str(e))
                await asyncio.sleep(1)


pub_sub_manager = RedisPubSubManager()
