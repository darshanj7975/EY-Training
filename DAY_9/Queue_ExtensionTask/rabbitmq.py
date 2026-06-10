from dotenv import load_dotenv
import os
import aio_pika

load_dotenv()

url = os.getenv("CLOUDAMQP_URL")

print(url)  # test
async def connect_rabbitmq():
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()

    return connection, channel