from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges
from datetime import datetime, timezone
from typing import Annotated
from pymongo import ASCENDING, IndexModel


class Inventory(Document):
    product_name: Annotated[str, Indexed()]
    product_price: float
    cost_price: float = 0.0
    amount_available: int
    min_stock_level: int = 5
    reorder_threshold: int = 10
    worker_shop_name: Annotated[str, Indexed()]
    branch_id: str | None = None
    branch_name: str | None = None
    sku: str | None = None  # SKU / barcode, unique per shop when set
    barcode: str | None = None
    category_id: str | None = None
    category_name: str | None = None
    supplier_name: str | None = None
    supplier_contact: str | None = None
    image_url: str | None = None
    tax_rate: float | None = None  # overrides shop-level tax if specified
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
            ),
            IndexModel(
                [("worker_shop_name", ASCENDING), ("barcode", ASCENDING)],
                unique=True,
                partialFilterExpression={"barcode": {"$type": "string"}},
            ),
        ]
