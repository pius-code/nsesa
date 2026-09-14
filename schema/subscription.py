from pydantic import BaseModel, Field
from typing import Optional, Literal


class PackageUpgradeRequest(BaseModel):
    package_tier: Literal["START-UP", "ELITE", "ENTERPRISE"]
    payment_mode: Literal["MOMO", "CARD", "BANK_TRANSFER"] = "MOMO"
    customer_phone: Optional[str] = None


class PackageEntitlementsResponse(BaseModel):
    shop_name: str
    package_tier: str
    status: str
    max_branches: int
    max_users: int
    max_products: int
    allow_advanced_reports: bool
    allow_custom_branding: bool
    allow_bulk_import: bool
    allow_api_access: bool
    current_branch_count: int
    current_user_count: int
    current_product_count: int
