from datetime import datetime, timezone, timedelta
from model.Expense import Expense
from model.Stakeholder import Stakeholder
from schema.expense import ExpenseCreate, ExpenseUpdate, ExpenseResponse
from beanie import PydanticObjectId
from fastapi import HTTPException


def _to_response(e: Expense) -> ExpenseResponse:
    return ExpenseResponse(
        id=str(e.id),
        title=e.title,
        amount=e.amount,
        category=e.category,
        note=e.note,
        date=e.date,
        shop_name=e.shop_name,
        recorded_by=e.recorded_by,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


async def _get_stakeholder(user_id: str) -> Stakeholder:
    user = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(user_id))
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return user


async def create_expense(payload: ExpenseCreate, user_id: str) -> ExpenseResponse:
    user = await _get_stakeholder(user_id)
    expense_date = payload.date if payload.date else datetime.now(timezone.utc)

    new_expense = Expense(
        title=payload.title.strip(),
        amount=round(payload.amount, 2),
        category=payload.category.strip() if payload.category else "Utilities",
        note=payload.note.strip() if payload.note else None,
        date=expense_date,
        shop_name=user.worker_shop_name,
        recorded_by=user.worker_name,
        recorded_by_id=str(user.id),
    )
    await new_expense.insert()
    return _to_response(new_expense)


async def get_shop_expenses(
    user_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    category: str | None = None,
    limit: int = 100,
    skip: int = 0,
) -> list[ExpenseResponse]:
    user = await _get_stakeholder(user_id)
    filters = [
        Expense.shop_name == user.worker_shop_name,
        Expense.is_deleted == False,
    ]

    if category and category.lower() != "all":
        filters.append(Expense.category == category)

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            filters.append(Expense.date >= start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
            filters.append(Expense.date < end_dt)
        except ValueError:
            pass

    expenses = await Expense.find(*filters).sort(-Expense.date).skip(skip).limit(limit).to_list()
    return [_to_response(e) for e in expenses]


async def update_expense(expense_id: str, payload: ExpenseUpdate, user_id: str) -> ExpenseResponse:
    user = await _get_stakeholder(user_id)
    expense = await Expense.get(PydanticObjectId(expense_id))
    if not expense or expense.is_deleted or expense.shop_name != user.worker_shop_name:
        raise HTTPException(status_code=404, detail="Expense not found")

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(expense, field, value)

    await expense.save()
    return _to_response(expense)


async def delete_expense(expense_id: str, user_id: str):
    user = await _get_stakeholder(user_id)
    expense = await Expense.get(PydanticObjectId(expense_id))
    if not expense or expense.is_deleted or expense.shop_name != user.worker_shop_name:
        raise HTTPException(status_code=404, detail="Expense not found")

    expense.is_deleted = True
    await expense.save()
    return {"message": "Expense deleted successfully"}
