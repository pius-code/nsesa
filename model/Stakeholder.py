# models/stakeholder.py
from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges # noqa
from datetime import datetime, timezone
from typing import Annotated


class Stakeholder(Document):
    worker_name: str
    worker_shop_name: Annotated[str, Indexed()]
    worker_branch_name: str
    worker_role: str  # "admin" | "worker"
    worker_email: Annotated[str, Indexed(unique=True)]
    worker_phone: str | None = None
    worker_hashed_password: str
    worker_shop_image: str = "https://res.cloudinary.com/dho3j5aqn/image/upload/v1780329934/simple1_jdsqio.avif" # noqa
    is_active: bool = True
    last_login: datetime | None = None
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "stakeholders"
