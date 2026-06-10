import asyncio
import aio_pika
from rabbitmq import connect_rabbitmq


async def publish():
    print("Starting publisher...")

    connection, channel = await connect_rabbitmq()

    print("Connected to RabbitMQ")

    message = aio_pika.Message(
        body=b"Payment Received"
    )

    await channel.default_exchange.publish(
        message,
        routing_key="payments"
    )

    print("Message Published")

    await connection.close()
    print("Connection Closed")
    print("FILE IS RUNNING")


asyncio.run(publish())