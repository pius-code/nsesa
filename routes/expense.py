from fastapi import APIRouter, Depends, Query
from schema.expense import ExpenseCreate, ExpenseUpdate, ExpenseResponse
from repository.expense import (
    create_expense,
    get_shop_expenses,
    update_expense,
    delete_expense,
)
from middleware.auth import admin_protected_route

router = APIRouter(prefix="/api/v1/expenses", tags=["expenses"])


@router.post("", response_model=ExpenseResponse)
async def add_expense(payload: ExpenseCreate, admin_id: str = Depends(admin_protected_route)):
    """Admin or super admin — record a new shop expense"""
    return await create_expense(payload, admin_id)


@router.get("", response_model=list[ExpenseResponse])
async def list_expenses(
    start_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    category: str | None = Query(default=None, description="Category filter"),
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    admin_id: str = Depends(admin_protected_route),
):
    """Admin or super admin — view expenses for their shop"""
    return await get_shop_expenses(
        user_id=admin_id,
        start_date=start_date,
        end_date=end_date,
        category=category,
        limit=limit,
        skip=skip,
    )


@router.patch("/{expense_id}", response_model=ExpenseResponse)
async def edit_expense(
    expense_id: str,
    payload: ExpenseUpdate,
    admin_id: str = Depends(admin_protected_route),
):
    """Admin or super admin — edit an existing expense"""
    return await update_expense(expense_id, payload, admin_id)


@router.delete("/{expense_id}")
async def remove_expense(
    expense_id: str,
    admin_id: str = Depends(admin_protected_route),
):
    """Admin or super admin — delete an expense"""
    return await delete_expense(expense_id, admin_id)
