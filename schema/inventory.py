from pydantic import BaseModel, Field
from typing import Optional


class InventoryCreate(BaseModel):
    product_name: str = Field(..., example="Product A")
    product_price: float = Field(..., example=19.99)
    amount_available: int = Field(..., example=100)


class InventoryUpdate(BaseModel):
    product_name: Optional[str] = Field(None, example="Product A")
    product_price: Optional[float] = Field(None, example=19.99)
    amount_available: Optional[int] = Field(None, example=100)
