from fastapi import APIRouter, Request, BackgroundTasks, Depends, Query
from schema.transaction import TransactionCreate, TransactionActionRequest, TransactionEditRequest # noqa
from repository.transaction import (
    save_an_nsesa_transaction,
    get_my_shop_transactions as fetch_shop_transactions,
    get_transaction_by_receipt_id,
    delete_transaction,
    refund_transaction,
    edit_transaction,
    get_transaction_history,
    get_processed_by_options,
)
from middleware.auth import get_current_user, admin_protected_route
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
async def get_my_shop_transactions(
    request: Request,
    start_date: str | None = Query(default=None, description="YYYY-MM-DD, inclusive"), # noqa
    end_date: str | None = Query(default=None, description="YYYY-MM-DD, inclusive"), # noqa
    processed_by: str | None = Query(default=None, description="Filter by worker name"), # noqa
    status: str | None = Query(default=None, description="success | returned | rejected"), # noqa
):
    """Get transactions for my shop, optionally filtered by date range / worker / status""" # noqa
    current_user = await get_current_user(request)
    shop_name = await get_stakeholder_worker_shop_name(str(current_user.get("sub"))) # noqa
    return await fetch_shop_transactions(
        shop_name=shop_name, start_date=start_date, end_date=end_date, # type: ignore # noqa
        processed_by=processed_by, status=status,
    )


@router.post("/transactions/{transaction_id}/delete")
async def remove_transaction(transaction_id: str, payload: TransactionActionRequest, admin=Depends(admin_protected_route)): # noqa
    """Admin only — soft delete a transaction, restock its items, and log why""" # noqa
    return await delete_transaction(transaction_id, payload, admin)  # type: ignore # noqa


@router.post("/transactions/{transaction_id}/refund")
async def refund_a_transaction(transaction_id: str, payload: TransactionActionRequest, background_tasks: BackgroundTasks, admin=Depends(admin_protected_route)): # noqa
    """Admin only — mark a transaction as returned, restock its items, log why, and SMS the customer if we have a number""" # noqa
    return await refund_transaction(transaction_id, payload, admin, background_tasks)  # type: ignore # noqa


@router.patch("/transactions/{transaction_id}")
async def edit_a_transaction(transaction_id: str, payload: TransactionEditRequest, admin=Depends(admin_protected_route)): # noqa
    """Admin only — edit customer details and/or line items on an active transaction""" # noqa
    return await edit_transaction(transaction_id, payload, admin)  # type: ignore # noqa


@router.get("/transactions/{transaction_id}/audit")
async def get_transaction_audit(transaction_id: str, admin=Depends(admin_protected_route)): # noqa
    """Admin only — full delete/refund/edit history for a transaction"""
    return await get_transaction_history(transaction_id, admin)  # type: ignore # noqa


@router.get("/transactions/processed_by_options")
async def list_processed_by_options(request: Request):
    """Any authenticated user — distinct worker names for the Person filter""" # noqa
    current_user = await get_current_user(request)
    shop_name = await get_stakeholder_worker_shop_name(str(current_user.get("sub"))) # noqa
    return await get_processed_by_options(shop_name)  # type: ignore
