import asyncio
from rabbitmq import connect_rabbitmq

async def test():
    connection, channel = await connect_rabbitmq()

    print("Connected Successfully!")

    await connection.close()

asyncio.run(test())