import asyncio
import aio_pika
from rabbitmq import connect_rabbitmq

async def setup():

    connection, channel = await connect_rabbitmq()

    dlx = await channel.declare_exchange(
        "dlx",
        aio_pika.ExchangeType.DIRECT,
        durable=True
    )

    dlq = await channel.declare_queue(
        "payments_dlq",
        durable=True
    )

    await dlq.bind(
        dlx,
        routing_key="payments"
    )

    await channel.declare_queue(
        "payments",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "dlx",
            "x-dead-letter-routing-key": "payments",
            "x-message-ttl": 86400000
        }
    )

    print("Queue Created!")

    await connection.close()

asyncio.run(setup())