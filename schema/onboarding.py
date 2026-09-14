from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class MerchantOnboardingRequest(BaseModel):
    business_name: str = Field(..., min_length=2, example="Starline Supermarket")
    business_type: str = Field(default="retail", example="supermarket")
    currency: str = Field(default="GHS")
    phone: str = Field(..., min_length=10, example="0244123456")
    email: EmailStr = Field(..., example="owner@starlinesupermarket.com")
    address: Optional[str] = Field(None, example="Spintex Road, Accra")
    password: str = Field(..., min_length=6)
    owner_name: str = Field(..., min_length=2, example="Kofi Owusu")
    package_tier: str = Field(default="START-UP", example="START-UP")
    main_branch_name: str = Field(default="Main Branch")
    tax_rate: float = Field(default=0.0)


class MerchantOnboardingResponse(BaseModel):
    message: str
    business_name: str
    token: str
    owner_id: str
    branch_id: str
