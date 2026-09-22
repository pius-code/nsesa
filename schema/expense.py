from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ExpenseCreate(BaseModel):
    title: str = Field(..., min_length=2, example="Electricity Token")
    amount: float = Field(..., gt=0, example=150.0)
    category: str = Field(default="Utilities", example="Utilities")
    note: Optional[str] = Field(None, example="Meter # 123456789")
    date: Optional[datetime] = None


class ExpenseUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    category: Optional[str] = None
    note: Optional[str] = None
    date: Optional[datetime] = None


class ExpenseResponse(BaseModel):
    id: str
    title: str
    amount: float
    category: str
    note: Optional[str] = None
    date: datetime
    shop_name: str
    recorded_by: str
    created_at: datetime
    updated_at: datetime
