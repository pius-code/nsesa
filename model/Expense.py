from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges
from datetime import datetime, timezone
from typing import Annotated
from pymongo import ASCENDING, IndexModel


class Expense(Document):
    title: str
    amount: float
    category: str  # e.g., "Utilities", "Rent", "Salaries", "Maintenance", "Logistics", "Other"
    note: str | None = None
    date: datetime = datetime.now(timezone.utc)
    shop_name: Annotated[str, Indexed()]
    recorded_by: str
    recorded_by_id: str
    is_deleted: bool = False
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "expenses"
        indexes = [
            IndexModel(
                [("shop_name", ASCENDING), ("date", ASCENDING)],
            )
        ]
