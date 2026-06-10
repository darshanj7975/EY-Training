import asyncio
from rabbitmq import connect_rabbitmq

async def consume():
    

    connection, channel = await connect_rabbitmq()
    

    queue = await channel.get_queue("payments")
    

    print("Waiting for messages...")

    await asyncio.Future()  # keep program running forever

asyncio.run(consume())