from fastapi import APIRouter, Request, BackgroundTasks
from schema.transaction import TransactionCreate
from repository.transaction import (
    save_an_nsesa_transaction,
    get_my_shop_transactions as fetch_shop_transactions,
    get_transaction_by_receipt_id,
)
from middleware.auth import get_current_user
from repository.stakeholder import get_stakeholder_worker_shop_name

router = APIRouter(prefix="/api/v1", tags=["transaction"])


@router.post("/create-transaction")
async def create_transaction(payload: TransactionCreate, request: Request, background_tasks: BackgroundTasks):  # noqa
    """Save a new transaction to the database"""
    current_user = await get_current_user(request)
    shop_name = await get_stakeholder_worker_shop_name(str(current_user.get("sub"))) # noqa
    return await save_an_nsesa_transaction(payload, shop_name=shop_name, background_tasks=background_tasks)  # type: ignore # noqa


@router.get("/receipt/{receipt_id}")
async def get_receipt(receipt_id: str):
    """Public route — returns a transaction by receipt ID"""
    return await get_transaction_by_receipt_id(receipt_id)


@router.get("/return_my_shop_transactions")
async def get_my_shop_transactions(request: Request):
    """Get all transactions for my shop"""
    current_user = await get_current_user(request)
    shop_name = await get_stakeholder_worker_shop_name(str(current_user.get("sub"))) # noqa
    return await fetch_shop_transactions(shop_name=shop_name)  # type: ignore # noqa
