from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

PaymentStatus = Literal[
    "PENDING",
    "SUCCESS",
    "FAILED",
    "CANCELLED",
    "REFUNDED",
    "RECONCILED",
    "REVERSED"
]

PaymentMode = Literal[
    "CASH",
    "MOMO",
    "CARD",
    "BANK_TRANSFER",
    "QR",
    "PAY_LATER"
]


class Payment(Document):
    payment_reference: Annotated[str, Indexed(unique=True)]
    idempotency_key: Annotated[str | None, Indexed(unique=True)] = None
    transaction_id: Annotated[str | None, Indexed()] = None
    receipt_id: Annotated[str | None, Indexed()] = None
    shop_name: Annotated[str, Indexed()]
    branch_name: str | None = None
    amount: float
    currency: str = "GHS"
    payment_mode: Annotated[PaymentMode, Indexed()]
    payment_provider: str  # "CASH", "HUBTEL", "PAYSTACK", "ARKESEL", "BANK", "INTERNAL_LEDGER"
    provider_reference: str | None = None
    status: Annotated[PaymentStatus, Indexed()] = "PENDING"
    failure_reason: str | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None
    processed_by_id: str | None = None
    processed_by_name: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "payments"
