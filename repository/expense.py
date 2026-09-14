from datetime import datetime, timezone
from fastapi import HTTPException
from beanie import PydanticObjectId
from model.Expense import Expense
from schema.expense import ExpenseCreate, ExpenseUpdate


class ExpenseService:
    @staticmethod
    async def create_expense(payload: ExpenseCreate, shop_name: str, user_id: str, user_name: str) -> Expense:
        expense = Expense(
            shop_name=shop_name,
            branch_name=payload.branch_name or "Main Branch",
            title=payload.title,
            category=payload.category.upper(),
            amount=payload.amount,
            currency=payload.currency or "GHS",
            payment_mode=payload.payment_mode.upper(),
            expense_date=payload.expense_date or datetime.now(timezone.utc),
            notes=payload.notes,
            receipt_image=payload.receipt_image,
            recorded_by_id=user_id,
            recorded_by_name=user_name,
        )
        await expense.insert()
        return expense

    @staticmethod
    async def get_expenses(
        shop_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        category: str | None = None,
        limit: int = 50,
        skip: int = 0
    ) -> list[Expense]:
        query = [Expense.shop_name == shop_name, Expense.is_deleted == False]
        if category:
            query.append(Expense.category == category.upper())
        if start_date:
            query.append(Expense.expense_date >= start_date)
        if end_date:
            query.append(Expense.expense_date <= end_date)

        return await Expense.find(*query).sort(-Expense.expense_date).skip(skip).limit(limit).to_list()

    @staticmethod
    async def update_expense(expense_id: str, payload: ExpenseUpdate, shop_name: str) -> Expense:
        try:
            exp = await Expense.get(PydanticObjectId(expense_id))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid expense ID")

        if not exp or exp.shop_name != shop_name or exp.is_deleted:
            raise HTTPException(status_code=404, detail="Expense not found")

        if payload.title is not None:
            exp.title = payload.title
        if payload.category is not None:
            exp.category = payload.category.upper()
        if payload.amount is not None:
            exp.amount = payload.amount
        if payload.payment_mode is not None:
            exp.payment_mode = payload.payment_mode.upper()
        if payload.expense_date is not None:
            exp.expense_date = payload.expense_date
        if payload.notes is not None:
            exp.notes = payload.notes
        if payload.receipt_image is not None:
            exp.receipt_image = payload.receipt_image

        await exp.save()
        return exp

    @staticmethod
    async def delete_expense(expense_id: str, shop_name: str) -> dict:
        try:
            exp = await Expense.get(PydanticObjectId(expense_id))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid expense ID")

        if not exp or exp.shop_name != shop_name:
            raise HTTPException(status_code=404, detail="Expense not found")

        exp.is_deleted = True
        await exp.save()
        return {"message": "Expense deleted successfully"}
