# models/transaction.py
from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges # noqa
from datetime import datetime, timezone
from typing import Annotated, List
from pydantic import BaseModel


class TransactionItem(BaseModel):
    product_id: str
    product_name: str
    unit_price: float
    quantity: int
    subtotal: float


class Transaction(Document):
    customer_name: str  # auto-generated or user-provided
    items: List[TransactionItem]
    total_price: float
    customer_number: str | None = None
    customer_email: str | None = None
    processed_by: Annotated[str, Indexed()]  # worker ID
    status: str = "success"  # success | returned | rejected
    synced_at: datetime | None = None  # None means pending sync from local
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "transactions"
