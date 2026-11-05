import asyncio
import logging

import aio_pika
import httpx

from app.config import settings
from app.rate_limiter import ProviderRateLimiter

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

async def main():
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    limiter = ProviderRateLimiter()

    try:
        channel = await connection.channel()

        await channel.set_qos(prefetch_count=1)

        queue = await channel.declare_queue(settings.rabbitmq_queue,durable=True)

        async with httpx.AsyncClient(timeout=10.0) as client:
            async with queue.iterator() as messages:
                async for message in messages:
                    vehicle_id = message.body.decode()

                    try:
                        # Shared redis rate-limiter
                        await limiter.acquire()

                        response = await client.get(  f"{settings.provider_url}/prices/{vehicle_id}")

                        response.raise_for_status()

                        price = response.json()

                        logger.info(
                            "Processed %s: %s %s",
                            vehicle_id,
                            price["market_price"],
                            price["currency"],
                        )

                        # Acknowledge only after success
                        await message.ack()

                    except Exception:
                        logger.exception(
                            "Failed to process %s",
                            vehicle_id,
                        )

                        raise

    finally:
        await connection.close()
        await limiter.close()


if __name__ == "__main__":
    asyncio.run(main())



