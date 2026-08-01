from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges # noqa
from datetime import datetime, timezone
from typing import Annotated
from pymongo import ASCENDING, IndexModel


class Category(Document):
    name: Annotated[str, Indexed()]
    description: str | None = None
    worker_shop_name: Annotated[str, Indexed()]
    created_by: str
    is_deleted: bool = False
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "categories"
        indexes = [
            IndexModel(
                [("worker_shop_name", ASCENDING), ("name", ASCENDING)],
                unique=True,
            )
        ]
