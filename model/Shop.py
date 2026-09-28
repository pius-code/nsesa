from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges # noqa
from datetime import datetime, timezone
from typing import Annotated


class Shop(Document):
    name: Annotated[str, Indexed(unique=True)]
    logo_url: str | None = None
    location: str | None = None
    phone: str | None = None
    email: str | None = None
    description: str | None = None
    currency: str = "GH₵"
    status: str = "active"  # active | suspended | deleted
    status_reason: str | None = None
    status_changed_by: str | None = None
    status_changed_at: datetime | None = None
    sms_sent_count: int = 0
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "shops"
