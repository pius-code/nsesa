from model.TransactionAudit import TransactionAudit
from typing import Any


async def log_transaction_action(
    transaction_id: str,
    action: str,
    performed_by: str,
    performed_by_name: str,
    reason: str,
    at_shop: str,
    changes: dict[str, Any] | None = None,
):
    entry = TransactionAudit(
        transaction_id=transaction_id,
        action=action,
        performed_by=performed_by,
        performed_by_name=performed_by_name,
        reason=reason,
        changes=changes,
        at_shop=at_shop,
    )
    await entry.insert()
    return entry


async def get_transaction_audit_log(transaction_id: str, at_shop: str):
    entries = await TransactionAudit.find(
        TransactionAudit.transaction_id == transaction_id,
        TransactionAudit.at_shop == at_shop,
    ).sort(-TransactionAudit.created_at).to_list() # noqa
    return entries
