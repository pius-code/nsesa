from pydantic import BaseModel
from typing import Optional, List


class TransactionItemCreate(BaseModel):
    product_id: str
    product_name: str
    unit_price: float
    quantity: int
    subtotal: float


class TransactionCreate(BaseModel):
    customer_name: str
    items: List[TransactionItemCreate]
    total_price: float
    customer_number: Optional[str] = None
    customer_email: Optional[str] = None
    processed_by: str  # worker ID
