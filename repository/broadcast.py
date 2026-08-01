# repository/broadcast.py
from model.Transaction import Transaction
from model.Client import Client
from model.Stakeholder import Stakeholder
from beanie import PydanticObjectId
from fastapi import HTTPException, BackgroundTasks
from utils.arkesel_sms import send_broadcast_sms


async def _get_admin_shop(admin_id: str) -> str:
    admin = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(admin_id)) # noqa
    if not admin:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return admin.worker_shop_name


async def get_broadcast_recipients(shop_name: str) -> list[str]:
    """Everyone who's ever bought from this shop, by phone number — both
    registered clients and walk-in customer numbers captured at checkout."""
    tx_collection = Transaction.get_pymongo_collection()
    tx_numbers = await tx_collection.distinct(
        "customer_number", {"at_shop": shop_name, "customer_number": {"$nin": [None, ""]}} # noqa
    )

    client_collection = Client.get_pymongo_collection()
    client_numbers = await client_collection.distinct(
        "client_phone",
        {"worker_shop_name": shop_name, "is_deleted": False, "client_phone": {"$nin": [None, ""]}}, # noqa
    )

    combined = {n.strip() for n in [*tx_numbers, *client_numbers] if n and n.strip()} # noqa
    return sorted(combined)


async def count_broadcast_recipients(admin_id: str) -> dict:
    shop_name = await _get_admin_shop(admin_id)
    recipients = await get_broadcast_recipients(shop_name)
    return {"recipient_count": len(recipients)}


async def send_shop_broadcast(message: str, admin_id: str, background_tasks: BackgroundTasks): # noqa
    shop_name = await _get_admin_shop(admin_id)
    recipients = await get_broadcast_recipients(shop_name)

    if not recipients:
        raise HTTPException(status_code=400, detail="No customers with a phone number found for this shop") # noqa

    background_tasks.add_task(send_broadcast_sms, recipients, message)
    return {
        "message": f"Broadcast queued to {len(recipients)} customer(s)",
        "recipient_count": len(recipients),
    }


async def get_shop_admin_recipients() -> list[str]:
    """Every distinct phone number on file for a shop admin/super_admin account.""" # noqa
    collection = Stakeholder.get_pymongo_collection()
    numbers = await collection.distinct(
        "worker_phone",
        {"worker_role": {"$in": ["admin", "super_admin"]}, "worker_phone": {"$nin": [None, ""]}}, # noqa
    )
    return sorted({n.strip() for n in numbers if n and n.strip()})


async def count_shop_admin_recipients() -> dict:
    recipients = await get_shop_admin_recipients()
    return {"recipient_count": len(recipients)}


async def send_shop_admin_broadcast(message: str, background_tasks: BackgroundTasks): # noqa
    recipients = await get_shop_admin_recipients()
    if not recipients:
        raise HTTPException(
            status_code=400,
            detail="No shop admins have a phone number on file yet",
        )

    background_tasks.add_task(send_broadcast_sms, recipients, message)
    return {
        "message": f"Broadcast queued to {len(recipients)} shop admin(s)",
        "recipient_count": len(recipients),
    }
