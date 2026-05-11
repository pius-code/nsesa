# models/stakeholder.py
from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges
from datetime import datetime, timezone
from typing import Annotated


class Stakeholder(Document):
    worker_name: str
    worker_shop_name: str
    worker_branch_name: str
    worker_role: str  # "admin" | "worker"
    worker_email: Annotated[str, Indexed(unique=True)]
    worker_hashed_password: str
    is_active: bool = True
    last_login: datetime | None = None
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "stakeholders"
