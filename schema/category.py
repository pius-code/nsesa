from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CategoryCreate(BaseModel):
    name: str = Field(..., example="Beverages")
    description: Optional[str] = Field(None, example="Drinks and beverages")


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, example="Beverages")
    description: Optional[str] = Field(None, example="Drinks and beverages")


class CategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    worker_shop_name: str
    created_by: str
    created_at: datetime
    updated_at: datetime
