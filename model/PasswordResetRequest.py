from beanie import Document, Indexed
from datetime import datetime, timezone
from typing import Annotated, Optional


class PasswordResetRequest(Document):
    worker_id: Annotated[str, Indexed()]
    worker_name: str
    worker_email: Annotated[str, Indexed()]
    worker_phone: Optional[str] = None
    worker_branch_name: Optional[str] = None
    shop_name: Annotated[str, Indexed()]
    status: Annotated[str, Indexed()] = "pending"  # "pending" | "resolved" | "dismissed"
    requested_at: datetime = datetime.now(timezone.utc)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None

    class Settings:
        name = "password_reset_requests"
