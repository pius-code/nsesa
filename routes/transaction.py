from fastapi import APIRouter
from schema.transaction import TransactionCreate
from repository.transaction import save_an_nsesa_transaction

router = APIRouter(prefix="/api/v1", tags=["transaction"])


@router.post("/create-transaction")
async def create_transaction(payload: TransactionCreate):  # noqa
    """Save a new transaction to the database"""
    return await save_an_nsesa_transaction(payload)  # type: ignore
