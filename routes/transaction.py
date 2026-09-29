from fastapi import APIRouter, Request, BackgroundTasks, Depends, Query
from schema.transaction import TransactionCreate, TransactionActionRequest, TransactionEditRequest, ResendReceiptRequest, CompletePaymentRequest, AddItemsRequest # noqa
from repository.transaction import (
    save_an_nsesa_transaction,
    get_my_shop_transactions as fetch_shop_transactions,
    get_transaction_by_receipt_id,
    delete_transaction,
    refund_transaction,
    edit_transaction,
    get_transaction_history,
    get_processed_by_options,
    resend_receipt,
    complete_pending_payment,
    add_items_to_pending_order,
    cancel_pending_order,
)
from middleware.auth import get_current_user, require_permission, require_any_permission
from repository.stakeholder import get_stakeholder_worker_shop_name
from model.Stakeholder import Stakeholder
from beanie import PydanticObjectId

router = APIRouter(prefix="/api/v1", tags=["transaction"])


@router.post("/create-transaction")
async def create_transaction(
    payload: TransactionCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_permission("can_sell")),
):  # noqa
    """Save a new transaction to the database (requires can_sell)"""
    shop_name = await get_stakeholder_worker_shop_name(user_id) # noqa
    return await save_an_nsesa_transaction(payload, shop_name=shop_name, background_tasks=background_tasks, user_id=user_id)  # type: ignore # noqa


@router.get("/receipt/{receipt_id}")
async def get_receipt(receipt_id: str):
    """Public route — returns a transaction by receipt ID"""
    return await get_transaction_by_receipt_id(receipt_id)


@router.get("/return_my_shop_transactions")
async def get_my_shop_transactions(
    start_date: str | None = Query(default=None, description="YYYY-MM-DD, inclusive"), # noqa
    end_date: str | None = Query(default=None, description="YYYY-MM-DD, inclusive"), # noqa
    processed_by: str | None = Query(default=None, description="Filter by worker name"), # noqa
    status: str | None = Query(default=None, description="success | returned | rejected"), # noqa
    branch_name: str | None = Query(default=None, description="Filter by branch name"), # noqa
    user_id: str = Depends(require_any_permission("view_own_transactions", "view_all_transactions")),
):
    """Get transactions for my shop, optionally filtered by date range / worker / status / branch""" # noqa
    worker = await Stakeholder.get(PydanticObjectId(user_id))
    if not worker:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Worker not found")

    effective_processed_by = processed_by
    perms = worker.permissions or {}
    # Workers without view_all_transactions can only see their own
    if not perms.get("view_all_transactions", False) and worker.worker_role not in ("admin", "super_admin"):
        effective_processed_by = worker.worker_name

    return await fetch_shop_transactions(
        shop_name=worker.worker_shop_name,
        start_date=start_date,
        end_date=end_date,
        processed_by=effective_processed_by,
        status=status,
        branch_name=branch_name,
    )


@router.post("/transactions/{transaction_id}/delete")
async def remove_transaction(transaction_id: str, payload: TransactionActionRequest, worker_id=Depends(require_permission("can_manage_orders"))): # noqa
    """Permission: can_manage_orders — soft delete a transaction, restock its items, and log why""" # noqa
    return await delete_transaction(transaction_id, payload, worker_id)  # type: ignore # noqa


@router.post("/transactions/{transaction_id}/refund")
async def refund_a_transaction(transaction_id: str, payload: TransactionActionRequest, background_tasks: BackgroundTasks, worker_id=Depends(require_permission("can_manage_orders"))): # noqa
    """Permission: can_manage_orders — mark a transaction as returned, restock its items, log why, and SMS the customer if we have a number""" # noqa
    return await refund_transaction(transaction_id, payload, worker_id, background_tasks)  # type: ignore # noqa


@router.patch("/transactions/{transaction_id}")
async def edit_a_transaction(transaction_id: str, payload: TransactionEditRequest, worker_id=Depends(require_permission("can_manage_orders"))): # noqa
    """Permission: can_manage_orders — edit customer details and/or line items on an active transaction""" # noqa
    return await edit_transaction(transaction_id, payload, worker_id)  # type: ignore # noqa


@router.get("/transactions/{transaction_id}/audit")
async def get_transaction_audit(transaction_id: str, worker_id=Depends(require_permission("can_manage_orders"))): # noqa
    """Permission: can_manage_orders — full delete/refund/edit history for a transaction"""
    return await get_transaction_history(transaction_id, worker_id)  # type: ignore # noqa


@router.get("/transactions/processed_by_options")
async def list_processed_by_options(request: Request):
    """Any authenticated user — distinct worker names for the Person filter""" # noqa
    current_user = await get_current_user(request)
    user_id = str(current_user.get("sub"))
    worker = await Stakeholder.get(PydanticObjectId(user_id))
    if not worker:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Worker not found")

    if worker.worker_role == "worker":
        return [worker.worker_name]

    return await get_processed_by_options(worker.worker_shop_name)


@router.post("/transactions/{transaction_id}/resend-receipt")
async def resend_transaction_receipt(
    transaction_id: str,
    payload: ResendReceiptRequest,
    background_tasks: BackgroundTasks,
    worker_id: str = Depends(require_any_permission("can_sell", "can_manage_orders")),
): # noqa
    """Resend receipt SMS (requires can_sell or can_manage_orders)"""
    return await resend_receipt(transaction_id, payload, worker_id, background_tasks) # type: ignore # noqa


@router.post("/transactions/{transaction_id}/complete-payment")
async def complete_payment(
    transaction_id: str,
    payload: CompletePaymentRequest,
    background_tasks: BackgroundTasks,
    worker_id: str = Depends(require_permission("can_manage_orders")),
): # noqa
    """Record payment on a pending order (requires can_manage_orders)"""
    return await complete_pending_payment(transaction_id, payload, worker_id, background_tasks) # type: ignore # noqa


@router.post("/transactions/{transaction_id}/add-items")
async def add_items(
    transaction_id: str,
    payload: AddItemsRequest,
    worker_id: str = Depends(require_permission("can_manage_orders")),
): # noqa
    """Add more items to an open pending tab (requires can_manage_orders)"""
    return await add_items_to_pending_order(transaction_id, payload, worker_id) # type: ignore # noqa


@router.post("/transactions/{transaction_id}/cancel")
async def cancel_order(
    transaction_id: str,
    payload: TransactionActionRequest,
    worker_id: str = Depends(require_permission("can_manage_orders")),
): # noqa
    """Cancel a pending order that was never paid (requires can_manage_orders)"""
    return await cancel_pending_order(transaction_id, payload, worker_id) # type: ignore # noqa
