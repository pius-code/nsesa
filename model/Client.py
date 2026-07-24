from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges # noqa
from datetime import datetime, timezone
from typing import Annotated
from pymongo import ASCENDING, IndexModel


class Client(Document):
    client_name: Annotated[str, Indexed()]
    client_phone: str | None = None
    client_email: str | None = None
    worker_shop_name: Annotated[str, Indexed()]
    notes: str | None = None
    created_by: str
    is_deleted: bool = False
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "clients"
        indexes = [
            IndexModel(
                [("worker_shop_name", ASCENDING), ("client_phone", ASCENDING)],
                unique=True,
                partialFilterExpression={"client_phone": {"$type": "string"}},
            )
        ]
