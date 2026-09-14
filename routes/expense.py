from datetime import datetime
from fastapi import APIRouter, Depends
from model.Stakeholder import Stakeholder
from middleware.auth import get_current_stakeholder, require_roles
from schema.expense import ExpenseCreate, ExpenseUpdate
from repository.expense import ExpenseService

expense_router = APIRouter(prefix="/api/v1/expenses", tags=["Expenses & Bookkeeping"])


@expense_router.post("")
async def create_expense(
    payload: ExpenseCreate,
    current_user: Stakeholder = Depends(require_roles(["owner", "admin", "manager", "accountant"]))
):
    return await ExpenseService.create_expense(
        payload=payload,
        shop_name=current_user.worker_shop_name,
        user_id=str(current_user.id),
        user_name=current_user.worker_name
    )


@expense_router.get("")
async def list_expenses(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    category: str | None = None,
    limit: int = 50,
    skip: int = 0,
    current_user: Stakeholder = Depends(require_roles(["owner", "admin", "manager", "accountant"]))
):
    return await ExpenseService.get_expenses(
        shop_name=current_user.worker_shop_name,
        start_date=start_date,
        end_date=end_date,
        category=category,
        limit=limit,
        skip=skip
    )


@expense_router.patch("/{expense_id}")
async def update_expense(
    expense_id: str,
    payload: ExpenseUpdate,
    current_user: Stakeholder = Depends(require_roles(["owner", "admin", "manager", "accountant"]))
):
    return await ExpenseService.update_expense(
        expense_id=expense_id,
        payload=payload,
        shop_name=current_user.worker_shop_name
    )


@expense_router.delete("/{expense_id}")
async def delete_expense(
    expense_id: str,
    current_user: Stakeholder = Depends(require_roles(["owner", "admin"]))
):
    return await ExpenseService.delete_expense(
        expense_id=expense_id,
        shop_name=current_user.worker_shop_name
    )
