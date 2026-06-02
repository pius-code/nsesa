# repository/transaction.py
from fastapi import HTTPException, BackgroundTasks
from beanie import PydanticObjectId
from model.Transaction import Transaction, TransactionItem
from schema.transaction import TransactionCreate
from model.Inventory import Inventory
from model.Stakeholder import Stakeholder
from utils.arkesel_sms import send_transaction_receipt_sms
import os

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


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
    try:
        worker = await Stakeholder.find_one(
            Stakeholder.id == PydanticObjectId(payload.processed_by_id)
        ) if payload.processed_by_id else None
        shop_image = worker.worker_shop_image if worker else None
    except Exception:
        shop_image = None

    new_id = PydanticObjectId()
    receipt_id = f"{shop_name}_{str(new_id)[-8:].upper()}"
    new_transaction = Transaction(
        id=new_id,
        receipt_id=receipt_id,
        shop_image=shop_image,
        customer_name=payload.customer_name,
        items=[TransactionItem(**item.model_dump()) for item in payload.items],  # noqa
        total_price=payload.total_price,
        customer_number=payload.customer_number,
        customer_email=payload.customer_email,
        payment_mode=payload.payment_mode,
        processed_by=payload.processed_by,
        processed_by_id=payload.processed_by_id,
        at_shop=shop_name
    )
    await new_transaction.insert()  # noqa

    if payload.send_sms and new_transaction.customer_number and background_tasks:
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


async def get_my_shop_transactions(shop_name: str):
    """Get all transactions for my shop"""
    transactions = await Transaction.find(Transaction.at_shop == shop_name).to_list()  # noqa
    return transactions


async def get_transaction_by_receipt_id(receipt_id: str):
    transaction = await Transaction.find_one(Transaction.receipt_id == receipt_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Receipt not found")

    if not transaction.shop_image:
        admin = await Stakeholder.find_one(
            Stakeholder.worker_shop_name == transaction.at_shop
        )
        if admin:
            transaction.shop_image = admin.worker_shop_image

    return transaction
