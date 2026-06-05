from typing import Dict

orders_db: Dict[int, dict] = {}

current_id = 1


def get_db():
    return orders_db