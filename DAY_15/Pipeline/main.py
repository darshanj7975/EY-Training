import os
import json
import asyncio

from fastapi import FastAPI, HTTPException

# IMPORTANT: Async Service Bus client
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage

from azure.cosmos import CosmosClient
from groq import Groq

app = FastAPI(title="Pipeline API with Groq")

# ==========================================================
# CONFIGURATION
# ==========================================================

SB_CONN_STR =""
QUEUE_NAME = "Restapi"

COSMOS_URI = ""
COSMOS_KEY = ""

GROQ_API_KEY = ""

# ==========================================================
# COSMOS DB
# ==========================================================

cosmos_client = CosmosClient(
    COSMOS_URI,
    credential=COSMOS_KEY
)

db = cosmos_client.get_database_client("PipelineDB")
container = db.get_container_client("Items")

# ==========================================================
# GROQ
# ==========================================================

groq_client = Groq(
    api_key=GROQ_API_KEY
)

# ==========================================================
# HEALTH CHECK
# ==========================================================

@app.get("/")
async def home():
    return {
        "status": "running",
        "service": "Pipeline API"
    }

# ==========================================================
# INGEST DATA
# ==========================================================

@app.post("/ingest")
async def ingest_data(payload: dict):

    try:

        async with ServiceBusClient.from_connection_string(
            conn_str=SB_CONN_STR
        ) as client:

            sender = client.get_queue_sender(
                queue_name=QUEUE_NAME
            )

            async with sender:

                message = ServiceBusMessage(
                    json.dumps(payload)
                )

                await sender.send_messages(message)

        return {
            "status": "success",
            "message": "Message queued successfully"
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# ==========================================================
# ANALYZE ITEM USING GROQ
# ==========================================================

@app.get("/extend/{item_id}")
async def extend_with_groq(item_id: str):

    try:

        item = container.read_item(
            item=item_id,
            partition_key=item_id
        )

    except Exception:

        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )

    try:

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content":
                    "You are a data analyst. Summarize and provide insights."
                },
                {
                    "role": "user",
                    "content":
                    f"Analyze this data:\n{json.dumps(item)}"
                }
            ],
            temperature=0.2,
            max_tokens=1024
        )

        return {
            "original_data": item,
            "analysis": response.choices[0].message.content
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Groq Error: {str(e)}"
        )

# ==========================================================
# LIST ALL ITEMS
# ==========================================================

@app.get("/items")
async def list_items():

    try:

        items = list(
            container.query_items(
                query="SELECT * FROM c",
                enable_cross_partition_query=True
            )
        )

        return {
            "count": len(items),
            "items": items
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# ==========================================================
# BACKGROUND QUEUE PROCESSOR
# ==========================================================

async def queue_processor():

    print("Queue Processor Started")

    while True:

        try:

            async with ServiceBusClient.from_connection_string(
                conn_str=SB_CONN_STR
            ) as client:

                receiver = client.get_queue_receiver(
                    queue_name=QUEUE_NAME
                )

                async with receiver:

                    messages = await receiver.receive_messages(
                        max_message_count=10,
                        max_wait_time=5
                    )

                    for msg in messages:

                        try:

                            body = b"".join(
                                msg.body
                            ).decode("utf-8")

                            payload = json.loads(body)

                            document = {
                                "id": str(msg.sequence_number),
                                "content": payload
                            }

                            container.upsert_item(document)

                            await receiver.complete_message(msg)

                            print(
                                f"Saved Message: {msg.sequence_number}"
                            )

                        except Exception as msg_error:

                            print(
                                f"Message Error: {msg_error}"
                            )

        except Exception as e:

            print(
                f"Processor Error: {e}"
            )

        await asyncio.sleep(2)

# ==========================================================
# STARTUP
# ==========================================================

@app.on_event("startup")
async def startup_event():

    asyncio.create_task(
        queue_processor()
    )