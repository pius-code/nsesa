from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges
from datetime import datetime, timezone
from typing import Annotated


class Inventory(Document):
    product_name: Annotated[str, Indexed()]
    product_price: float
    amount_available: int
    is_available: bool = True  # flips to False when amount_available hits 0
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "inventory"
