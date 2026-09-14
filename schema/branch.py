from pydantic import BaseModel, Field
from typing import Optional


class BranchCreate(BaseModel):
    branch_name: str = Field(..., min_length=2, example="Osu Branch")
    location: Optional[str] = Field(None, example="Oxford Street, Accra")
    phone: Optional[str] = Field(None, example="0244000000")
    is_main: bool = False


class BranchUpdate(BaseModel):
    branch_name: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    is_main: Optional[bool] = None
    is_active: Optional[bool] = None


class BranchResponse(BaseModel):
    id: str
    shop_name: str
    branch_name: str
    location: Optional[str] = None
    phone: Optional[str] = None
    is_main: bool
    is_active: bool
