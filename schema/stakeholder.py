from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


DEFAULT_SHOP_IMAGE = ( # noqa
    "https://res.cloudinary.com/dho3j5aqn/image/upload"
    "/v1780329934/simple1_jdsqio.avif"
)


class WorkerPermissions(BaseModel):
    """Full permission set for a worker. All flags default to False."""
    # Scope
    is_global: bool = False              # True = sees whole shop, False = branch-scoped
    # Sales
    can_sell: bool = False               # Can create & complete transactions
    can_manage_orders: bool = False      # Can see and complete pending orders
    # Transactions visibility
    view_own_transactions: bool = False  # Can view own transactions only
    view_all_transactions: bool = False  # Can view all transactions in shop
    # Inventory
    can_add_inventory: bool = False      # Can add new inventory items
    can_update_stock: bool = False       # Can restock existing items (atomic with add)
    # People management
    can_add_others: bool = False         # Can create workers & set their permissions
    # Expenses
    can_manage_expenses: bool = False    # Can add & edit expenses
    # Reports
    can_view_own_branch_report: bool = False  # Can view own branch financial report
    can_view_all_reports: bool = False        # Can view all branch reports
    can_view_specific_branches: List[str] = []  # Specific branch report access
    # Categories
    can_add_categories: bool = False     # Can add & edit product categories
    # SMS
    can_sms_own_branch: bool = False     # Can send SMS to own branch customers only
    can_sms_all_branches: bool = False   # Can send SMS to all shop customers
    # Clients
    can_see_clients: bool = False        # Can view client list & details
    can_add_clients: bool = False        # Can create new clients
    can_edit_clients: bool = False       # Can edit client details
    # Profile
    can_edit_profile: bool = False       # Can edit their profile name & details
    # Branches
    can_manage_branches: bool = False    # Can create and manage shop branches


def admin_permissions() -> dict:
    """Full permissions — given to existing admins and new admins on creation."""
    return WorkerPermissions(
        is_global=True,
        can_sell=True,
        can_manage_orders=True,
        view_own_transactions=True,
        view_all_transactions=True,
        can_add_inventory=True,
        can_update_stock=True,
        can_add_others=True,
        can_manage_expenses=True,
        can_view_own_branch_report=True,
        can_view_all_reports=True,
        can_add_categories=True,
        can_sms_own_branch=True,
        can_sms_all_branches=True,
        can_see_clients=True,
        can_add_clients=True,
        can_edit_clients=True,
        can_edit_profile=True,
        can_manage_branches=True,
    ).model_dump()


def worker_default_permissions() -> dict:
    """Minimal permissions — given to existing workers on migration."""
    return WorkerPermissions(
        can_sell=True,
        view_own_transactions=True,
    ).model_dump()


import re
from pydantic import field_validator

def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must contain at least one letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one number.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+[\];/]", password):
        raise ValueError("Password must contain at least one special character/symbol (e.g. !@#$%^&*).")
    return password


class StakeholderCreate(BaseModel):
    worker_name: str
    worker_shop_name: str
    worker_branch_name: Optional[str] = None
    worker_role: str  # "admin" | "worker"
    worker_email: str
    worker_phone: Optional[str] = None
    worker_password: str
    worker_shop_image: Optional[str] = DEFAULT_SHOP_IMAGE

    @field_validator("worker_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class adminStakeholderCreateWorker(BaseModel):
    worker_name: str
    role_label: str = ""               # e.g. "Cashier", "Store Manager" — display name
    worker_branch_name: Optional[str] = None
    worker_email: str
    worker_phone: str                  # Required for alerts and reset notifications
    worker_password: str
    permissions: Optional[WorkerPermissions] = None  # None = default worker perms

    @field_validator("worker_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class ForgotPasswordRequest(BaseModel):
    email: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class AdminResetPasswordRequest(BaseModel):
    new_password: str
    reason: str
    send_sms: bool = True

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)



class StakeholderLogin(BaseModel):
    worker_email: str
    worker_password: str


class ShopImageUpdate(BaseModel):
    worker_shop_image: str


class WorkerPermissionsUpdate(BaseModel):
    """Used for PATCH /workers/{id}/permissions — can update permissions and role_label."""
    role_label: Optional[str] = None
    permissions: WorkerPermissions


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
    role_label: str = ""
    worker_email: str
    worker_phone: Optional[str] = None
    worker_shop_image: str
    permissions: dict = {}
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    worker_phone: str
    worker_name: Optional[str] = None


