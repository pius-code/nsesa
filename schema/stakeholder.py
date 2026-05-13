from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StakeholderCreate(BaseModel):
    worker_name: str
    worker_shop_name: str
    worker_branch_name: Optional[str] = None
    worker_role: str  # "admin" | "worker"
    worker_email: str
    worker_password: str  # plain, will be hashed in the route


class adminStakeholderCreateWorker(BaseModel):
    worker_name: str
    worker_role: str  # "admin" | "worker"
    worker_email: str
    worker_password: str   # default to admin for this schema


class StakeholderLogin(BaseModel):
    worker_email: str
    worker_password: str


class StakeholderUpdate(BaseModel):
    worker_name: Optional[str] = None
    worker_shop_name: Optional[str] = None
    worker_branch_name: Optional[str] = None
    worker_role: Optional[str] = None
    is_active: Optional[bool] = None


class StakeholderResponse(BaseModel):
    id: str
    worker_name: str
    worker_shop_name: str
    worker_branch_name: str
    worker_role: str
    worker_email: str
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
