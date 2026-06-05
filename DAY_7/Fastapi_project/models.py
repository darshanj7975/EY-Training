from pydantic import BaseModel
from typing import List, Optional


class OrderItem(BaseModel):
    product_name: str
    quantity: int
    price: float


class OrderCreate(BaseModel):
    customer_name: str
    items: List[OrderItem]


class OrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    items: Optional[List[OrderItem]] = None


class OrderResponse(BaseModel):
    id: int
    customer_name: str
    items: List[OrderItem]
    total_amount: float