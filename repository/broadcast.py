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


async def get_broadcast_recipients_details(shop_name: str) -> list[dict]:
    """Everyone who's ever bought from this shop — both registered clients
    and walk-in customer numbers captured at checkout, returned with names."""
    by_phone: dict[str, str] = {}

    # Registered clients
    clients = await Client.find(
        Client.worker_shop_name == shop_name,
        Client.is_deleted == False,
    ).to_list()
    for c in clients:
        if c.client_phone and c.client_phone.strip():
            phone = c.client_phone.strip()
            name = c.client_name.strip() if c.client_name else "Client"
            by_phone[phone] = name

    # Walk-in transaction customers
    txs = await Transaction.find(
        Transaction.at_shop == shop_name,
        Or(Transaction.is_deleted == False, Transaction.is_deleted == None),
    ).to_list()
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


async def get_broadcast_recipients(shop_name: str) -> list[str]:
    details = await get_broadcast_recipients_details(shop_name)
    return [r["phone"] for r in details]


async def count_broadcast_recipients(admin_id: str) -> dict:
    shop_name = await _get_admin_shop(admin_id)
    recipients = await get_broadcast_recipients_details(shop_name)
    return {
        "recipient_count": len(recipients),
        "recipients": recipients,
    }


async def send_shop_broadcast(message: str, admin_id: str, background_tasks: BackgroundTasks): # noqa
    shop_name = await _get_admin_shop(admin_id)
    recipients = await get_broadcast_recipients_details(shop_name)

    if not recipients:
        raise HTTPException(status_code=400, detail="No customers with a phone number found for this shop") # noqa

    phone_numbers = [r["phone"] for r in recipients]
    background_tasks.add_task(send_broadcast_sms, phone_numbers, message)
    return {
        "message": f"Broadcast queued to {len(recipients)} customer(s)",
        "recipient_count": len(recipients),
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
