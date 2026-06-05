# models.py
from pydantic import BaseModel, Field
from typing import Optional

class Item(BaseModel):
    id: int
    name: str = Field(..., example="Sample Item")
    price: float = Field(..., gt=0)
    description: Optional[str] = None