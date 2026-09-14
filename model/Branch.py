from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges
from datetime import datetime, timezone
from typing import Annotated


class Branch(Document):
    business_id: Annotated[str, Indexed()]
    shop_name: Annotated[str, Indexed()]  # business name reference
    branch_name: Annotated[str, Indexed()]
    location: str | None = None
    phone: str | None = None
    is_main: bool = False
    is_active: bool = True
    created_by: str
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "branches"
