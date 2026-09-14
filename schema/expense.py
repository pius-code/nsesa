from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ExpenseCreate(BaseModel):
    title: str = Field(..., min_length=2, example="ECG Electricity Bill")
    category: str = Field(..., example="UTILITIES")  # RENT, UTILITIES, SALARIES, RESTOCK, SUPPLIES, LOGISTICS, OTHER
    amount: float = Field(..., gt=0, example=350.00)
    currency: str = "GHS"
    payment_mode: str = "CASH"  # CASH, MOMO, BANK_TRANSFER, CARD
    expense_date: Optional[datetime] = None
    notes: Optional[str] = None
    receipt_image: Optional[str] = None
    branch_name: Optional[str] = "Main Branch"


class ExpenseUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    payment_mode: Optional[str] = None
    expense_date: Optional[datetime] = None
    notes: Optional[str] = None
    receipt_image: Optional[str] = None
