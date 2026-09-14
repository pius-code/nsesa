from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges
from datetime import datetime, timezone
from typing import Annotated


class Expense(Document):
    shop_name: Annotated[str, Indexed()]
    branch_name: str | None = None
    title: str
    category: Annotated[str, Indexed()]  # "RENT", "UTILITIES", "SALARIES", "RESTOCK", "SUPPLIES", "LOGISTICS", "OTHER"
    amount: float
    currency: str = "GHS"
    payment_mode: str = "CASH"  # CASH, MOMO, BANK_TRANSFER, CARD
    expense_date: datetime = datetime.now(timezone.utc)
    notes: str | None = None
    receipt_image: str | None = None
    recorded_by_id: str
    recorded_by_name: str
    is_deleted: bool = False
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "expenses"
