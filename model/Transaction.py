# models/transaction.py
from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges
from datetime import datetime, timezone
from typing import Annotated, List
from pydantic import BaseModel


class TransactionItem(BaseModel):
    product_id: str
    product_name: str
    unit_price: float
    unit_cost: float = 0.0
    quantity: int
    discount: float = 0.0
    tax_rate: float = 0.0
    subtotal: float
    refunded_quantity: int = 0


class Transaction(Document):
    customer_name: str
    items: List[TransactionItem]
    subtotal: float = 0.0
    discount_total: float = 0.0
    tax_total: float = 0.0
    total_price: float
    receipt_id: str | None = None
    shop_image: str | None = None
    customer_number: str | None = None
    customer_email: str | None = None
    client_id: str | None = None
    payment_mode: str | None = None  # CASH | MOMO | CARD | BANK_TRANSFER | QR | PAY_LATER
    payment_id: str | None = None
    payment_reference: str | None = None
    note: str | None = None  # e.g. "no pepper, vegetarian, sugar-free"
    processed_by: Annotated[str, Indexed()]  # worker name
    processed_by_id: str | None = None
    branch_name: str | None = "Main Branch"
    branch_id: str | None = None
    status: str = "success"  # success | refunded | partially_refunded | rejected | cancelled
    refund_amount: float = 0.0
    refund_reason: str | None = None
    refunded_by_id: str | None = None
    refunded_by_name: str | None = None
    refunded_at: datetime | None = None
    is_deleted: bool = False
    synced_at: datetime | None = None  # None means pending sync from local
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)
    at_shop: Annotated[str, Indexed()]

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "transactions"
