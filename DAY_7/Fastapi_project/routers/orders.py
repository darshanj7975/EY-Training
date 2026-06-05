from fastapi import APIRouter, Depends, HTTPException
from models import OrderCreate, OrderUpdate
from database import get_db
import database

router = APIRouter(prefix="/orders", tags=["Orders"])


def calculate_total(items):
    return sum(item.quantity * item.price for item in items)


@router.post("/", status_code=201)
def create_order(order: OrderCreate, db=Depends(get_db)):
    order_id = database.current_id
    database.current_id += 1

    data = {
        "id": order_id,
        "customer_name": order.customer_name,
        "items": [item.dict() for item in order.items],
        "total_amount": calculate_total(order.items)
    }

    db[order_id] = data
    return data


@router.get("/")
def get_orders(db=Depends(get_db)):
    return list(db.values())


#patch
@router.patch("/{order_id}")
def patch_order(order_id: int, order: OrderUpdate, db=Depends(get_db)):

    if order_id not in db:
        raise HTTPException(status_code=404, detail="Order not found")

    existing = db[order_id]

    update_data = order.dict(exclude_unset=True)

    if "customer_name" in update_data:
        existing["customer_name"] = update_data["customer_name"]

    if "items" in update_data:
        existing["items"] = [item.dict() for item in update_data["items"]]
        existing["total_amount"] = calculate_total(update_data["items"])

    db[order_id] = existing

    return existing