from beanie import Document, Indexed
from datetime import datetime, timezone
from typing import Annotated, Optional


class PasswordResetAuditLog(Document):
    worker_id: Annotated[str, Indexed()]
    worker_name: str
    changed_by_id: Annotated[str, Indexed()]
    changed_by_name: str
    changed_by_role: str
    reason: str
    shop_name: Annotated[str, Indexed()]
    timestamp: datetime = datetime.now(timezone.utc)
    notes: Optional[str] = None

    class Settings:
        name = "password_reset_audit_logs"
