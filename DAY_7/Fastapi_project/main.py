from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.orders import router as order_router

app = FastAPI(
    title="E-Commerce Order Management API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(order_router)


@app.get("/")
def home():
    return {"message": "Order Management API Running"}