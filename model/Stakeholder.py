# models/stakeholder.py
from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges
from datetime import datetime, timezone
from typing import Annotated, List


class Stakeholder(Document):
    worker_name: str
    worker_shop_name: Annotated[str, Indexed()]
    worker_branch_name: str = "Main Branch"
    worker_branch_id: str | None = None
    worker_role: str  # "super_admin" | "owner" | "admin" | "manager" | "cashier" | "inventory_manager" | "accountant" | "worker"
    permissions: List[str] = []
    worker_email: Annotated[str, Indexed(unique=True)]
    worker_phone: str | None = None
    worker_hashed_password: str
    worker_shop_image: str = "https://res.cloudinary.com/dho3j5aqn/image/upload/v1780329934/simple1_jdsqio.avif"
    is_active: bool = True
    last_login: datetime | None = None
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "stakeholders"
