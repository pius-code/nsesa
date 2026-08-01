from pydantic import BaseModel, Field
from typing import Optional, List


class TransactionItemCreate(BaseModel):
    product_id: str
    product_name: str
    unit_price: float
    quantity: int
    subtotal: float


class TransactionCreate(BaseModel):
    customer_name: Optional[str] = "customer"
    items: List[TransactionItemCreate]
    total_price: float
    customer_number: Optional[str] = None
    customer_email: Optional[str] = None
    client_id: Optional[str] = None
    payment_mode: Optional[str] = None
    processed_by: str  # worker name
    processed_by_id: Optional[str] = None
    send_sms: bool = False
    pay_later: bool = False  # open tab — saved as "pending", no payment mode/SMS yet # noqa
    note: Optional[str] = Field(None, example="No pepper, extra sugar-free syrup") # noqa


class TransactionActionRequest(BaseModel):
    """Used for delete and refund — every mutation to a completed sale must be justified.""" # noqa
    reason: str = Field(..., min_length=3, example="Customer cancelled order")


class TransactionEditRequest(BaseModel):
    reason: str = Field(..., min_length=3, example="Fixed customer phone number") # noqa
    customer_name: Optional[str] = None
    customer_number: Optional[str] = None
    customer_email: Optional[str] = None
    payment_mode: Optional[str] = None
    note: Optional[str] = None
    items: Optional[List[TransactionItemCreate]] = None


class ResendReceiptRequest(BaseModel):
    customer_number: str = Field(..., min_length=6, example="0244000000")


class CompletePaymentRequest(BaseModel):
    payment_mode: str = Field(..., example="cash")
    send_sms: bool = False


class AddItemsRequest(BaseModel):
    items: List[TransactionItemCreate]
    note: Optional[str] = None
