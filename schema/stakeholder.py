from pydantic import BaseModel
from typing import Optional
from datetime import datetime


DEFAULT_SHOP_IMAGE = ( # noqa
    "https://res.cloudinary.com/dho3j5aqn/image/upload"
    "/v1780329934/simple1_jdsqio.avif"
)


class StakeholderCreate(BaseModel):
    worker_name: str
    worker_shop_name: str
    worker_branch_name: Optional[str] = None
    worker_role: str  # "admin" | "worker"
    worker_email: str
    worker_phone: Optional[str] = None
    worker_password: str  # plain, will be hashed in the route
    worker_shop_image: Optional[str] = DEFAULT_SHOP_IMAGE


class adminStakeholderCreateWorker(BaseModel):
    worker_name: str
    worker_role: str  # "admin" | "worker"
    worker_email: str
    worker_phone: Optional[str] = None
    worker_password: str   # default to admin for this schema


class StakeholderLogin(BaseModel):
    worker_email: str
    worker_password: str


class ShopImageUpdate(BaseModel):
    worker_shop_image: str


class StakeholderUpdate(BaseModel):
    worker_name: Optional[str] = None
    worker_shop_name: Optional[str] = None
    worker_branch_name: Optional[str] = None
    worker_role: Optional[str] = None
    worker_phone: Optional[str] = None
    is_active: Optional[bool] = None


class StakeholderResponse(BaseModel):
    id: str
    worker_name: str
    worker_shop_name: str
    worker_branch_name: str
    worker_role: str
    worker_email: str
    worker_phone: Optional[str] = None
    worker_shop_image: str
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
