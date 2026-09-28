from beanie import Document, Indexed
from datetime import datetime, timezone
from typing import Annotated, Literal

StockMovementType = Literal[
    "RESTOCK",
    "SALE",
    "REFUND",
    "TRANSFER_IN",
    "TRANSFER_OUT",
    "ADJUSTMENT",
    "DAMAGE",
    "AUDIT"
]


class StockMovement(Document):
    product_id: Annotated[str, Indexed()]
    product_name: str
    sku: str | None = None
    shop_name: Annotated[str, Indexed()]
    branch_name: str | None = None
    movement_type: Annotated[StockMovementType, Indexed()] = "RESTOCK"
    quantity_change: int  # positive for addition (+50), negative for deduction (-1)
    previous_quantity: int
    new_quantity: int
    unit_cost: float = 0.0
    unit_price: float = 0.0
    reference_id: str | None = None  # e.g. transaction_id or invoice_no
    performed_by_id: str
    performed_by_name: str
    reason: str = "No reason given"
    created_at: datetime = datetime.now(timezone.utc)

    class Settings:
        name = "stock_movements"
