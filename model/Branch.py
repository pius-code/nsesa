from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges
from datetime import datetime, timezone
from typing import Annotated
from pymongo import ASCENDING, IndexModel


class Branch(Document):
    shop_name: Annotated[str, Indexed()]
    branch_name: Annotated[str, Indexed()]
    location: str | None = None
    phone: str | None = None
    is_main: bool = False
    is_active: bool = True
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "branches"
        indexes = [
            IndexModel(
                [("shop_name", ASCENDING), ("branch_name", ASCENDING)],
                unique=True,
            )
        ]
