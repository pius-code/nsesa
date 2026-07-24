from beanie import Document, Indexed
from datetime import datetime, timezone
from typing import Annotated, Any


class TransactionAudit(Document):
    transaction_id: Annotated[str, Indexed()]
    action: str  # "deleted" | "refunded" | "edited"
    performed_by: str  # stakeholder id
    performed_by_name: str
    reason: str
    changes: dict[str, Any] | None = None  # {field: {"old": ..., "new": ...}}
    at_shop: Annotated[str, Indexed()]
    created_at: datetime = datetime.now(timezone.utc)

    class Settings:
        name = "transaction_audits"
