from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges # noqa
from datetime import datetime, timezone
from typing import Annotated
from pymongo import ASCENDING, IndexModel


class Inventory(Document):
    product_name: Annotated[str, Indexed()]
    product_price: float
    amount_available: int
    worker_shop_name: Annotated[str, Indexed()]
    sku: str | None = None  # SKU / barcode, unique per shop when set
    category_id: str | None = None
    category_name: str | None = None
    is_available: bool = True  # flips to False when amount_available hits 0
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)
    created_by: str
    is_deleted: bool = False

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "inventory"
        indexes = [
            IndexModel(
                [("worker_shop_name", ASCENDING), ("sku", ASCENDING)],
                unique=True,
                partialFilterExpression={"sku": {"$type": "string"}},
            )
        ]
