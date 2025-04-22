import asyncio
import logging
from datetime import timedelta
from typing import Optional

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
        self.pubsub = None
        self.redis_connection = None
        self.celery_connection = False

    async def _get_redis_connection(self) -> aioredis.Redis:
        """
        Establishes a connection to Redis.
        Returns:
            aioredis.Redis: Redis connection object.
        """
        if self.redis_connection:
            return self.redis_connection

        logger.info("Creating new redis client")
        self.celery_connection = True
        self.redis_connection = aioredis.Redis.from_url(
            settings.REDIS_URL.unicode_string(),
            decode_responses=True,
        )
        return self.redis_connection

    async def connect(self) -> None:
        """
        Connects to the Redis server.
        """
        self.redis_connection = await self._get_redis_connection()
        self.pubsub = self.redis_connection.pubsub()

    async def disconnect(self) -> None:
        """
        Disconnects from the Redis server.
        """
        if self.pubsub:
            await self.pubsub.close()
            self.pubsub = None  # Clear pubsub reference
        if self.redis_connection:
            await self.redis_connection.close()
            self.redis_connection = None  # Clear redis connection reference

    async def publish(self, room_id: str, message: str) -> None:
        if settings.ENVIRONMENT == Environment.DEBUG:
            return

        if not self.redis_connection:
            logger.error("Redis client is not connected")
            return

        try:
            logger.info(f"Publishing message to {room_id}: {message}")
            await self.redis_connection.publish(room_id, message)
        except ConnectionError as e:
            logger.error(f"Failed to publish message: {e}")

    async def subscribe(self, room_id: str) -> aioredis.Redis:
        if not self.pubsub:
            await self.connect()  # Ensure we are connected before subscribing
        await self.pubsub.subscribe(room_id)
        logger.info(f"Subscribed to {room_id}")
        return self.pubsub

    async def unsubscribe(self, room_id: str) -> None:
        """
        Unsubscribes from a Redis channel.
        Args:
            room_id (str): Channel or room ID to unsubscribe from.
        """
        if self.pubsub:
            await self.pubsub.unsubscribe(room_id)

    async def get_subscribers_count(self, room_id: str) -> int:
        """
        Returns the number of subscribers to a Redis channel.

        Args:
            room_id (str): Channel or room ID.

        Returns:
            int: Number of subscribers to the channel.
        """
        members = await self.redis_connection.smembers(room_id)
        return len(members)


pub_sub_manager = RedisPubSubManager()
