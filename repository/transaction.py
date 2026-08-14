# repository/transaction.py
from fastapi import HTTPException, BackgroundTasks
from beanie import PydanticObjectId
from model.Transaction import Transaction, TransactionItem
from schema.transaction import TransactionCreate, TransactionActionRequest, TransactionEditRequest, ResendReceiptRequest, CompletePaymentRequest, AddItemsRequest # noqa
from model.Inventory import Inventory
from model.Stakeholder import Stakeholder
from model.Client import Client
from beanie.operators import Or, In
from utils.arkesel_sms import send_transaction_receipt_sms, send_refund_notice_sms # noqa
from repository.transaction_audit import log_transaction_action, get_transaction_audit_log # noqa
from datetime import datetime, timedelta, timezone
import os
import re

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def _slugify_shop_name(shop_name: str) -> str:
    # Shop names are free text (spaces, apostrophes, "&", etc.) but this
    # becomes a literal URL path segment for the receipt link — anything
    # that isn't alphanumeric collapses to a single hyphen so the link
    # never breaks, whether it's clicked in a browser or tapped from an SMS. # noqa
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", shop_name).strip("-")
    return slug.lower() or "shop"


async def save_an_nsesa_transaction(payload: TransactionCreate, shop_name: str, background_tasks: BackgroundTasks = None): # noqa
    # 1. Fetch and validate inventory items before taking any action
    inventory_items_map = {} # noqa 
    for item in payload.items:
        try:
            inventory_item = await Inventory.get(PydanticObjectId(item.product_id))  # noqa
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid product ID format for {item.product_name}")  # noqa

        if not inventory_item:
            raise HTTPException(
                status_code=404,  # noqa
                detail=f"Product '{item.product_name}' not found in inventory."
            ) # noqa          
        if inventory_item.amount_available < item.quantity:
            raise HTTPException(
                status_code=400,  # noqa
                detail=f"Not enough stock for '{item.product_name}'. Only {inventory_item.amount_available} available."  # noqa
            )

        inventory_items_map[item.product_id] = inventory_item

    # 3. Apply atomic decrements directly in the database using inc()
    for item in payload.items:
        inv_item_record = inventory_items_map[item.product_id]
        new_amount = inv_item_record.amount_available - item.quantity
        await inv_item_record.inc({Inventory.amount_available: -item.quantity})  # noqa
        if new_amount <= 0:
            await inv_item_record.set({  # noqa
                Inventory.is_available: False,
                Inventory.amount_available: 0
            })

    # 4. Save the actual transaction document
    shop_image = None
    try:
        admin = await Stakeholder.find_one(
            Stakeholder.worker_shop_name == shop_name,
            In(Stakeholder.worker_role, ["admin", "super_admin"]),
        )
        if admin and admin.worker_shop_image:
            shop_image = admin.worker_shop_image
        elif payload.processed_by_id:
            worker = await Stakeholder.get(PydanticObjectId(payload.processed_by_id))
            if worker:
                shop_image = worker.worker_shop_image
    except Exception:
        shop_image = None

    # Resolve a registered client, if one was picked, and snapshot their
    # details onto the transaction (customer_name/number/email stay as
    # explicit overrides if the caller already sent them)
    customer_name = payload.customer_name
    customer_number = payload.customer_number
    customer_email = payload.customer_email
    if payload.client_id:
        client = await Client.get(PydanticObjectId(payload.client_id))
        if not client or client.is_deleted or client.worker_shop_name != shop_name: # noqa
            raise HTTPException(status_code=404, detail="Client not found")
        customer_name = customer_name or client.client_name
        customer_number = customer_number or client.client_phone
        customer_email = customer_email or client.client_email

    new_id = PydanticObjectId()
    # Hyphen, not underscore: underscore isn't in the GSM-7 default SMS
    # alphabet, so it needs an escape sequence to send over SMS — some
    # phones/gateways mis-render that escape as literal characters (e.g.
    # "%11") when the link is tapped from a text message, breaking the URL. # noqa
    receipt_id = f"{_slugify_shop_name(shop_name)}-{str(new_id)[-8:].upper()}" # noqa
    new_transaction = Transaction(
        id=new_id,
        receipt_id=receipt_id,
        shop_image=shop_image,
        customer_name=customer_name,
        items=[TransactionItem(**item.model_dump()) for item in payload.items],  # noqa
        total_price=payload.total_price,
        customer_number=customer_number,
        customer_email=customer_email,
        client_id=payload.client_id,
        payment_mode=None if payload.pay_later else payload.payment_mode,
        status="pending" if payload.pay_later else "success",
        note=payload.note,
        processed_by=payload.processed_by,
        processed_by_id=payload.processed_by_id,
        at_shop=shop_name
    )
    await new_transaction.insert()  # noqa

    # Pending (pay-later) orders haven't been paid yet — no receipt SMS until # noqa
    # payment is actually completed.
    if not payload.pay_later and payload.send_sms and new_transaction.customer_number and background_tasks: # noqa
        receipt_url = f"{FRONTEND_URL}/receipts/{new_transaction.receipt_id}"
        background_tasks.add_task(
            send_transaction_receipt_sms,
            phone_number=new_transaction.customer_number,
            customer_name=new_transaction.customer_name,
            transaction_id=str(new_transaction.id),
            shop_name=shop_name,
            total_price=new_transaction.total_price,
            items=[item.model_dump() for item in new_transaction.items],
            receipt_url=receipt_url,
            payment_mode=new_transaction.payment_mode,
        )

    return {
        "message": "Transaction saved successfully",
        "transaction_id": str(new_transaction.id),
    }


# Mongo's equality match {is_deleted: false} does NOT match documents where
# the field is absent entirely — and every transaction created before this
# field existed has no is_deleted key at all. {is_deleted: null} is the one
# Mongo query that matches both "explicitly null" and "field missing", so
# OR-ing it in treats old, field-less documents as not-deleted.
def _not_deleted():
    return Or(Transaction.is_deleted == False, Transaction.is_deleted == None) # noqa


async def get_my_shop_transactions(
    shop_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    processed_by: str | None = None,
    status: str | None = None,
):
    """Get transactions for my shop, optionally filtered by date range / worker / status""" # noqa
    filters = [Transaction.at_shop == shop_name, _not_deleted()]

    if status:
        filters.append(Transaction.status == status)
    if processed_by:
        filters.append(Transaction.processed_by == processed_by)
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) # noqa
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date must be YYYY-MM-DD") # noqa
        filters.append(Transaction.created_at >= start_dt)
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1) # noqa
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date must be YYYY-MM-DD") # noqa
        filters.append(Transaction.created_at < end_dt)

    return await Transaction.find(*filters).sort(-Transaction.created_at).to_list() # noqa


async def get_processed_by_options(shop_name: str) -> list[str]:
    """Distinct worker names who've processed a sale for this shop — powers the Person filter""" # noqa
    collection = Transaction.get_pymongo_collection()
    names = await collection.distinct("processed_by", {"at_shop": shop_name})
    return sorted(n for n in names if n)


async def get_transactions_by_client(client_id: str, shop_name: str):
    """Purchase history for a registered client, scoped to their shop"""
    return await Transaction.find(
        Transaction.client_id == client_id,
        Transaction.at_shop == shop_name,
        _not_deleted(),
    ).sort(-Transaction.created_at).to_list() # noqa


async def get_transaction_by_receipt_id(receipt_id: str):
    transaction = await Transaction.find_one(
        Transaction.receipt_id == receipt_id, _not_deleted()
    )
    if not transaction:
        raise HTTPException(status_code=404, detail="Receipt not found")

    DEFAULT_FALLBACK = "https://res.cloudinary.com/dho3j5aqn/image/upload/v1780329934/simple1_jdsqio.avif"
    if not transaction.shop_image or transaction.shop_image == DEFAULT_FALLBACK:
        admin = await Stakeholder.find_one(
            Stakeholder.worker_shop_name == transaction.at_shop,
            In(Stakeholder.worker_role, ["admin", "super_admin"]),
        )
        if admin and admin.worker_shop_image:
            transaction.shop_image = admin.worker_shop_image

    return transaction


async def _get_admin_and_shop(admin_id: str) -> Stakeholder:
    admin = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(admin_id)) # noqa
    if not admin:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return admin


async def _get_transaction_in_shop(transaction_id: str, shop_name: str) -> Transaction: # noqa
    transaction = await Transaction.get(PydanticObjectId(transaction_id))
    if not transaction or transaction.is_deleted or transaction.at_shop != shop_name: # noqa
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


async def _restock_items(items: list[TransactionItem]):
    for item in items:
        try:
            inv = await Inventory.get(PydanticObjectId(item.product_id))
        except Exception:
            continue
        if not inv:
            continue
        await inv.inc({Inventory.amount_available: item.quantity})  # noqa
        if not inv.is_available:
            await inv.set({Inventory.is_available: True})  # noqa


async def delete_transaction(transaction_id: str, payload: TransactionActionRequest, admin_id: str): # noqa
    admin = await _get_admin_and_shop(admin_id)
    transaction = await _get_transaction_in_shop(transaction_id, admin.worker_shop_name) # noqa

    await _restock_items(transaction.items)
    transaction.is_deleted = True
    await transaction.save()

    await log_transaction_action(
        transaction_id=str(transaction.id),
        action="deleted",
        performed_by=admin_id,
        performed_by_name=admin.worker_name,
        reason=payload.reason,
        at_shop=admin.worker_shop_name,
    )
    return {"message": "Transaction deleted successfully"}


async def refund_transaction(
    transaction_id: str,
    payload: TransactionActionRequest,
    admin_id: str,
    background_tasks: BackgroundTasks | None = None,
):
    admin = await _get_admin_and_shop(admin_id)
    transaction = await _get_transaction_in_shop(transaction_id, admin.worker_shop_name) # noqa

    if transaction.status == "returned":
        raise HTTPException(status_code=400, detail="Transaction has already been refunded") # noqa

    await _restock_items(transaction.items)
    transaction.status = "returned"
    await transaction.save()

    await log_transaction_action(
        transaction_id=str(transaction.id),
        action="refunded",
        performed_by=admin_id,
        performed_by_name=admin.worker_name,
        reason=payload.reason,
        at_shop=admin.worker_shop_name,
    )

    # Proactively confirm the refund by SMS when we have a number on file —
    # customers who hear nothing are far more likely to dispute the charge.
    if transaction.customer_number and background_tasks and transaction.receipt_id: # noqa
        receipt_url = f"{FRONTEND_URL}/receipts/{transaction.receipt_id}"
        background_tasks.add_task(
            send_refund_notice_sms,
            phone_number=transaction.customer_number,
            customer_name=transaction.customer_name,
            transaction_id=str(transaction.id),
            shop_name=admin.worker_shop_name,
            total_price=transaction.total_price,
            receipt_url=receipt_url,
        )

    return {"message": "Transaction refunded successfully", "transaction": transaction} # noqa


async def edit_transaction(transaction_id: str, payload: TransactionEditRequest, admin_id: str): # noqa
    admin = await _get_admin_and_shop(admin_id)
    transaction = await _get_transaction_in_shop(transaction_id, admin.worker_shop_name) # noqa

    if transaction.status != "success":
        raise HTTPException(status_code=400, detail="Only active (non-refunded) transactions can be edited") # noqa

    changes: dict = {}

    for field in ("customer_name", "customer_number", "customer_email", "payment_mode", "note"): # noqa
        new_value = getattr(payload, field)
        if new_value is not None and new_value != getattr(transaction, field):
            changes[field] = {"old": getattr(transaction, field), "new": new_value} # noqa
            setattr(transaction, field, new_value)

    if payload.items is not None:
        old_quantities = {i.product_id: i.quantity for i in transaction.items}
        new_quantities = {i.product_id: i.quantity for i in payload.items}
        product_ids = set(old_quantities) | set(new_quantities)
        deltas = {
            pid: new_quantities.get(pid, 0) - old_quantities.get(pid, 0)
            for pid in product_ids
            if new_quantities.get(pid, 0) != old_quantities.get(pid, 0)
        }

        inventory_cache: dict[str, Inventory] = {}
        for product_id, delta in deltas.items():
            inv = await Inventory.get(PydanticObjectId(product_id))
            if not inv:
                raise HTTPException(status_code=404, detail=f"Product {product_id} not found") # noqa
            if delta > 0 and inv.amount_available < delta:
                raise HTTPException(
                    status_code=400,
                    detail=f"Not enough stock for '{inv.product_name}' to increase quantity", # noqa
                )
            inventory_cache[product_id] = inv

        for product_id, delta in deltas.items():
            inv = inventory_cache[product_id]
            await inv.inc({Inventory.amount_available: -delta})  # noqa
            new_amount = inv.amount_available - delta
            if new_amount <= 0:
                await inv.set({Inventory.is_available: False, Inventory.amount_available: 0}) # noqa
            elif not inv.is_available:
                await inv.set({Inventory.is_available: True})  # noqa

        new_total = sum(i.subtotal for i in payload.items)
        changes["items"] = {
            "old": [i.model_dump() for i in transaction.items],
            "new": [i.model_dump() for i in payload.items],
        }
        changes["total_price"] = {"old": transaction.total_price, "new": new_total} # noqa
        transaction.items = [TransactionItem(**i.model_dump()) for i in payload.items] # noqa
        transaction.total_price = new_total

    if not changes:
        return {"message": "No changes to apply"}

    await transaction.save()
    await log_transaction_action(
        transaction_id=str(transaction.id),
        action="edited",
        performed_by=admin_id,
        performed_by_name=admin.worker_name,
        reason=payload.reason,
        at_shop=admin.worker_shop_name,
        changes=changes,
    )
    return {"message": "Transaction updated successfully", "transaction": transaction} # noqa


async def get_transaction_history(transaction_id: str, admin_id: str):
    admin = await _get_admin_and_shop(admin_id)
    await _get_transaction_in_shop(transaction_id, admin.worker_shop_name)
    return await get_transaction_audit_log(transaction_id, admin.worker_shop_name) # noqa


async def resend_receipt(
    transaction_id: str,
    payload: ResendReceiptRequest,
    worker_id: str,
    background_tasks: BackgroundTasks,
):
    worker = await _get_admin_and_shop(worker_id)
    transaction = await _get_transaction_in_shop(transaction_id, worker.worker_shop_name) # noqa

    if not transaction.receipt_id:
        raise HTTPException(status_code=400, detail="This transaction has no receipt to send") # noqa

    number_changed = transaction.customer_number != payload.customer_number
    if number_changed:
        transaction.customer_number = payload.customer_number
        await transaction.save()

    receipt_url = f"{FRONTEND_URL}/receipts/{transaction.receipt_id}"
    background_tasks.add_task(
        send_transaction_receipt_sms,
        phone_number=payload.customer_number,
        customer_name=transaction.customer_name,
        transaction_id=str(transaction.id),
        shop_name=worker.worker_shop_name,
        total_price=transaction.total_price,
        items=[item.model_dump() for item in transaction.items],
        receipt_url=receipt_url,
        payment_mode=transaction.payment_mode,
    )

    await log_transaction_action(
        transaction_id=str(transaction.id),
        action="receipt_resent",
        performed_by=worker_id,
        performed_by_name=worker.worker_name,
        reason=(
            f"Resent to {payload.customer_number}"
            + (" (number corrected)" if number_changed else "")
        ),
        at_shop=worker.worker_shop_name,
    )

    return {"message": "Receipt resent successfully"}


async def complete_pending_payment(
    transaction_id: str,
    payload: CompletePaymentRequest,
    worker_id: str,
    background_tasks: BackgroundTasks | None,
):
    worker = await _get_admin_and_shop(worker_id)
    transaction = await _get_transaction_in_shop(transaction_id, worker.worker_shop_name) # noqa

    if transaction.status != "pending":
        raise HTTPException(status_code=400, detail="This order is not pending payment") # noqa

    transaction.status = "success"
    transaction.payment_mode = payload.payment_mode
    await transaction.save()

    await log_transaction_action(
        transaction_id=str(transaction.id),
        action="payment_completed",
        performed_by=worker_id,
        performed_by_name=worker.worker_name,
        reason=f"Paid via {payload.payment_mode}",
        at_shop=worker.worker_shop_name,
    )

    if payload.send_sms and transaction.customer_number and transaction.receipt_id and background_tasks: # noqa
        receipt_url = f"{FRONTEND_URL}/receipts/{transaction.receipt_id}"
        background_tasks.add_task(
            send_transaction_receipt_sms,
            phone_number=transaction.customer_number,
            customer_name=transaction.customer_name,
            transaction_id=str(transaction.id),
            shop_name=worker.worker_shop_name,
            total_price=transaction.total_price,
            items=[item.model_dump() for item in transaction.items],
            receipt_url=receipt_url,
            payment_mode=transaction.payment_mode,
        )

    return {"message": "Payment recorded successfully", "transaction": transaction} # noqa


async def add_items_to_pending_order(transaction_id: str, payload: AddItemsRequest, worker_id: str): # noqa
    worker = await _get_admin_and_shop(worker_id)
    transaction = await _get_transaction_in_shop(transaction_id, worker.worker_shop_name) # noqa

    if transaction.status != "pending":
        raise HTTPException(status_code=400, detail="Can only add items to a pending order") # noqa

    inventory_map: dict[str, Inventory] = {}
    for item in payload.items:
        inv = await Inventory.get(PydanticObjectId(item.product_id))
        if not inv:
            raise HTTPException(status_code=404, detail=f"Product '{item.product_name}' not found") # noqa
        if inv.amount_available < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock for '{item.product_name}'. Only {inv.amount_available} available.", # noqa
            )
        inventory_map[item.product_id] = inv

    for item in payload.items:
        inv = inventory_map[item.product_id]
        await inv.inc({Inventory.amount_available: -item.quantity})  # noqa
        new_amount = inv.amount_available - item.quantity
        if new_amount <= 0:
            await inv.set({Inventory.is_available: False, Inventory.amount_available: 0}) # noqa

    items_by_id = {i.product_id: i for i in transaction.items}
    for new_item in payload.items:
        existing = items_by_id.get(new_item.product_id)
        if existing:
            existing.quantity += new_item.quantity
            existing.subtotal += new_item.subtotal
        else:
            transaction.items.append(TransactionItem(**new_item.model_dump())) # noqa
            items_by_id[new_item.product_id] = transaction.items[-1]

    transaction.total_price = sum(i.subtotal for i in transaction.items)
    if payload.note is not None:
        transaction.note = payload.note
    await transaction.save()
    return {"message": "Items added successfully", "transaction": transaction}


async def cancel_pending_order(transaction_id: str, payload: TransactionActionRequest, worker_id: str): # noqa
    worker = await _get_admin_and_shop(worker_id)
    transaction = await _get_transaction_in_shop(transaction_id, worker.worker_shop_name) # noqa

    if transaction.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending orders can be cancelled this way — use delete for completed transactions", # noqa
        )

    await _restock_items(transaction.items)
    transaction.is_deleted = True
    await transaction.save()

    await log_transaction_action(
        transaction_id=str(transaction.id),
        action="cancelled",
        performed_by=worker_id,
        performed_by_name=worker.worker_name,
        reason=payload.reason,
        at_shop=worker.worker_shop_name,
    )
    return {"message": "Order cancelled successfully"}
