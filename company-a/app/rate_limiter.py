
import asyncio

from limits import parse
from limits.aio.storage import RedisStorage
from limits.aio.strategies import MovingWindowRateLimiter

from app.config import settings


class ProviderRateLimiter:
    def __init__(self):
        self.storage = RedisStorage(
            settings.redis_url,
            implementation="redispy",
        )
        self.limiter = MovingWindowRateLimiter(
            self.storage
        )
        self.limit = parse(settings.rate_limit)

    async def acquire(self):
        while True:
            allowed = await self.limiter.hit(
                self.limit,
                settings.rate_limit_key,
            )

            if allowed:
                return

            await asyncio.sleep(0.02)

    async def close(self):
        await self.storage.bridge.get_connection().aclose()
