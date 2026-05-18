# repository/transaction.py
from fastapi import HTTPException
from beanie import PydanticObjectId
from model.Transaction import Transaction, TransactionItem
from schema.transaction import TransactionCreate
from model.Inventory import Inventory


async def save_an_nsesa_transaction(payload: TransactionCreate, shop_name: str): # noqa
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
    new_transaction = Transaction(
        customer_name=payload.customer_name,
        items=[TransactionItem(**item.model_dump()) for item in payload.items],  # noqa
        total_price=payload.total_price,
        customer_number=payload.customer_number,
        customer_email=payload.customer_email,
        processed_by=payload.processed_by,
        at_shop=shop_name
    )
    await new_transaction.insert()  # noqa

    return {
        "message": "Transaction saved successfully",
        "transaction_id": str(new_transaction.id),
    }


async def get_my_shop_transactions(shop_name: str):
    """Get all transactions for my shop"""
    transactions = await Transaction.find(Transaction.at_shop == shop_name).to_list()  # noqa
    return transactions
