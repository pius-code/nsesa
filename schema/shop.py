from pydantic import BaseModel, Field
from datetime import datetime


class ShopStatusRequest(BaseModel):
    reason: str = Field(..., min_length=3, example="Repeated policy violations")


class ShopProfileUpdate(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    location: str | None = None
    phone: str | None = None
    email: str | None = None
    description: str | None = None
    currency: str | None = None


class ShopProfileResponse(BaseModel):
    name: str
    logo_url: str | None = None
    location: str | None = None
    phone: str | None = None
    email: str | None = None
    description: str | None = None
    currency: str = "GH₵"
    status: str = "active"
    created_at: datetime

