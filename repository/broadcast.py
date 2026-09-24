# repository/broadcast.py
from model.Transaction import Transaction
from model.Client import Client
from model.Stakeholder import Stakeholder
from beanie import PydanticObjectId
from beanie.operators import Or, In
from fastapi import HTTPException, BackgroundTasks
from utils.arkesel_sms import send_broadcast_sms


async def _get_admin_shop(admin_id: str) -> str:
    admin = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(admin_id)) # noqa
    if not admin:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return admin.worker_shop_name


async def get_broadcast_recipients_details(shop_name: str, branch_name: str | None = None) -> list[dict]:
    """Everyone who's ever bought from this shop (or specific branch) — both registered clients
    and walk-in customer numbers captured at checkout, returned with names."""
    by_phone: dict[str, str] = {}

    client_filters = [Client.worker_shop_name == shop_name, Client.is_deleted == False]
    tx_filters = [Transaction.at_shop == shop_name, Or(Transaction.is_deleted == False, Transaction.is_deleted == None)]

    if branch_name and branch_name.lower() != "all":
        client_filters.append(Client.branch_name == branch_name)
        tx_filters.append(Transaction.branch_name == branch_name)

    # Registered clients
    clients = await Client.find(*client_filters).to_list()
    for c in clients:
        if c.client_phone and c.client_phone.strip():
            phone = c.client_phone.strip()
            name = c.client_name.strip() if c.client_name else "Client"
            by_phone[phone] = name

    # Walk-in transaction customers
    txs = await Transaction.find(*tx_filters).to_list()
    for t in txs:
        if t.customer_number and t.customer_number.strip():
            phone = t.customer_number.strip()
            if phone not in by_phone:
                name = (
                    t.customer_name.strip()
                    if (t.customer_name and t.customer_name.lower() != "customer")
                    else "Customer"
                )
                by_phone[phone] = name

    sorted_phones = sorted(by_phone.keys())
    return [{"name": by_phone[p], "phone": p} for p in sorted_phones]


async def get_broadcast_recipients(shop_name: str, branch_name: str | None = None) -> list[str]:
    details = await get_broadcast_recipients_details(shop_name, branch_name)
    return [r["phone"] for r in details]


async def count_broadcast_recipients(user_id: str, branch_name: str | None = None) -> dict:
    user = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(user_id))
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    effective_branch = branch_name
    if user.worker_role not in ["admin", "super_admin"]:
        effective_branch = user.worker_branch_name or None

    recipients = await get_broadcast_recipients_details(user.worker_shop_name, effective_branch)
    return {
        "recipient_count": len(recipients),
        "recipients": recipients,
        "branch_name": effective_branch,
    }


async def send_shop_broadcast(message: str, user_id: str, background_tasks: BackgroundTasks, branch_name: str | None = None):
    user = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(user_id))
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    effective_branch = branch_name
    if user.worker_role not in ["admin", "super_admin"]:
        effective_branch = user.worker_branch_name or None

    recipients = await get_broadcast_recipients_details(user.worker_shop_name, effective_branch)

    if not recipients:
        raise HTTPException(status_code=400, detail="No customers with a phone number found for this selection")

    phone_numbers = [r["phone"] for r in recipients]
    background_tasks.add_task(send_broadcast_sms, phone_numbers, message, user.worker_shop_name)
    target_desc = f" ({effective_branch})" if effective_branch else ""
    return {
        "message": f"Broadcast queued to {len(recipients)} customer(s){target_desc}",
        "recipient_count": len(recipients),
        "branch_name": effective_branch,
    }


async def get_shop_admin_recipients_details() -> list[dict]:
    """Every distinct shop admin/super_admin with a phone number, returned with names."""
    by_phone: dict[str, str] = {}

    admins = await Stakeholder.find(
        In(Stakeholder.worker_role, ["admin", "super_admin"]),
    ).to_list()
    for a in admins:
        if a.worker_phone and a.worker_phone.strip():
            phone = a.worker_phone.strip()
            name = a.worker_name.strip() if a.worker_name else "Admin"
            by_phone[phone] = name

    sorted_phones = sorted(by_phone.keys())
    return [{"name": by_phone[p], "phone": p} for p in sorted_phones]


async def get_shop_admin_recipients() -> list[str]:
    details = await get_shop_admin_recipients_details()
    return [r["phone"] for r in details]


async def count_shop_admin_recipients() -> dict:
    recipients = await get_shop_admin_recipients_details()
    return {
        "recipient_count": len(recipients),
        "recipients": recipients,
    }


async def send_shop_admin_broadcast(message: str, background_tasks: BackgroundTasks): # noqa
    recipients = await get_shop_admin_recipients_details()
    if not recipients:
        raise HTTPException(
            status_code=400,
            detail="No shop admins have a phone number on file yet",
        )

    phone_numbers = [r["phone"] for r in recipients]
    background_tasks.add_task(send_broadcast_sms, phone_numbers, message)
    return {
        "message": f"Broadcast queued to {len(recipients)} shop admin(s)",
        "recipient_count": len(recipients),
    }
