from __future__ import annotations
from pydantic import BaseModel, Field

class CartItem(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=99)

class OrderCreate(BaseModel):
    items: list[CartItem]
