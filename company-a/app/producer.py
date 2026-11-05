
import aio_pika
from app.config import settings

RABBITMQ_URL = settings.rabbitmq_url
QUEUE_NAME = settings.rabbitmq_queue


async def publish_vehicle_ids(count: int) -> int:
    connection = await aio_pika.connect_robust(RABBITMQ_URL)

    try:
        channel = await connection.channel(
            publisher_confirms=True
        )

        queue = await channel.declare_queue(
            QUEUE_NAME,
            durable=True,
        )

        for index in range(1, count + 1):
            vehicle_id = f"VEH-{index:04d}"

            message = aio_pika.Message(
                body=vehicle_id.encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                message_id=vehicle_id,
                content_type="text/plain",
            )

            await channel.default_exchange.publish(
                message,
                routing_key=queue.name,
                mandatory=True,
            )

        return count

    finally:
        await connection.close()
