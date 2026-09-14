from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any

PaymentModeType = Literal["CASH", "MOMO", "CARD", "BANK_TRANSFER", "QR", "PAY_LATER"]


class PaymentInitiateRequest(BaseModel):
    transaction_id: Optional[str] = None
    receipt_id: Optional[str] = None
    amount: float = Field(..., gt=0, example=150.00)
    payment_mode: PaymentModeType = "CASH"
    payment_provider: Optional[str] = None  # "HUBTEL", "PAYSTACK", "CASH", "BANK", "INTERNAL"
    customer_phone: Optional[str] = Field(None, example="0244123456")
    customer_name: Optional[str] = Field(None, example="Kwame Mensah")
    customer_email: Optional[str] = Field(None, example="kwame@example.com")
    momo_network: Optional[Literal["MTN", "TELECEL", "AT"]] = None
    idempotency_key: Optional[str] = None
    branch_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentVerifyRequest(BaseModel):
    payment_reference: str
    provider_reference: Optional[str] = None


class PaymentReconcileRequest(BaseModel):
    payment_reference: str
    action: Literal["APPROVE", "REJECT", "REFUND"]
    reason: str = Field(..., min_length=3)
