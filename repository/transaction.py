from model.Transaction import Transaction, TransactionItem
from schema.transaction import TransactionCreate


async def save_an_nsesa_transaction(payload: TransactionCreate):
    new_transaction = Transaction(
        customer_name=payload.customer_name,
        items=[TransactionItem(**item.model_dump()) for item in payload.items],
        total_price=payload.total_price,
        customer_number=payload.customer_number,
        customer_email=payload.customer_email,
        processed_by=payload.processed_by,
    )
    await new_transaction.insert()
    return {
        "message": "Transaction saved successfully",
        "transaction_id": str(new_transaction.id),
    }
