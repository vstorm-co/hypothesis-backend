import logging
from datetime import timedelta
from typing import Optional

from redis import asyncio as aioredis
from redis.asyncio import Redis
from src.config import settings
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
        if redis_client:
            logger.info("Getting redis client from global variable (src.redis)")
            return redis_client

        if self.redis_connection:
            logger.info(
                "Getting redis client from instance variable (self.redis_connection)"
            )
            return self.redis_connection

        logger.info("Creating new redis client")
        self.celery_connection = True
        pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL.unicode_string(),
            # max_connections=10,
            decode_responses=True,
        )
        return aioredis.Redis(connection_pool=pool)

    async def connect(self) -> None:
        """
        Connects to the Redis server.

        Raises:
            ConnectionError: If unable to get a connection from the pool.
        """
        self.redis_connection = await self._get_redis_connection()
        self.pubsub = self.redis_connection.pubsub()

    async def disconnect(self) -> None:
        """
        Disconnects from the Redis server.
        """
        self.pubsub.close()
        self.redis_connection.close()

    async def publish(self, room_id: str, message: str) -> None:
        """
        Publishes a message to a specific Redis channel.

        Args:
            room_id (str): Channel or room ID.
            message (str): Message to be published.
        """
        if not self.redis_connection:
            logger.error("Redis connection not established.")
            logger.error("Redis client %s", redis_client)

            pool = aioredis.ConnectionPool.from_url(
                settings.REDIS_URL.unicode_string(),
                max_connections=10,
                decode_responses=True,
            )
            self.redis_connection = aioredis.Redis(connection_pool=pool)

        await self.redis_connection.publish(room_id, message)

    async def subscribe(self, room_id: str) -> aioredis.Redis:
        """
        Subscribes to a Redis channel.

        Args:
            room_id (str): Channel or room ID to subscribe to.

        Returns:
            aioredis.ChannelSubscribe: PubSub object for the subscribed channel.
        """
        await self.pubsub.subscribe(room_id)
        return self.pubsub

    async def unsubscribe(self, room_id: str) -> None:
        """
        Unsubscribes from a Redis channel.

        Args:
            room_id (str): Channel or room ID to unsubscribe from.
        """
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
