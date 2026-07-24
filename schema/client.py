from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ClientCreate(BaseModel):
    client_name: str = Field(..., example="Ama Owusu")
    client_phone: Optional[str] = Field(None, example="0244000000")
    client_email: Optional[str] = Field(None, example="ama@example.com")
    notes: Optional[str] = Field(None, example="Prefers momo payments")


class ClientUpdate(BaseModel):
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_email: Optional[str] = None
    notes: Optional[str] = None


class ClientResponse(BaseModel):
    id: str
    client_name: str
    client_phone: Optional[str] = None
    client_email: Optional[str] = None
    notes: Optional[str] = None
    worker_shop_name: str
    created_at: datetime
    updated_at: datetime
