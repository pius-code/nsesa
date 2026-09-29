from fastapi import APIRouter, HTTPException, Depends
from schema.stakeholder import StakeholderCreate, StakeholderLogin, StakeholderResponse # noqa
from repository.stakeholder import create_stakeholder, get_Stakeholder_by_email, get_stakeholder_hashed_password, get_stakeholder_by_id # noqa
from repository.shop import get_shop_status
from utils.hasher import verifyPwd
from helpers.auth import generate_token
from middleware.auth import super_admin_protected_route, get_current_user

router = APIRouter(prefix="/api/v1", tags=["stakeholder"])


@router.post("/registerme")
async def register_stakeholder(

    payload: StakeholderCreate,
    super_admin=Depends(super_admin_protected_route),
):  # noqa
    """Register a new stakeholder account"""
    return await create_stakeholder(payload)  # type: ignore


@router.post("/login")
async def login_stakeholder(payload: StakeholderLogin):
    """Login stakeholder and return JWT token"""
    stakeholder = await get_Stakeholder_by_email(payload.worker_email)
    if not stakeholder:
        raise HTTPException(status_code=404, detail="Stakeholder not found")
    hashed_password = await get_stakeholder_hashed_password(payload.worker_email) # noqa
    if not verifyPwd(payload.worker_password, str(hashed_password)):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not stakeholder.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account has been deactivated. Please contact your store administrator.",
        )

    shop = await get_shop_status(stakeholder.worker_shop_name)
    if shop and shop.status != "active":
        verb = "deleted" if shop.status == "deleted" else "suspended"
        raise HTTPException(
            status_code=403,
            detail=f"Your shop has been {verb}. Please contact the administrator.", # noqa
        )

    token = generate_token(str(stakeholder.id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "worker": StakeholderResponse(
            id=str(stakeholder.id),
            worker_name=stakeholder.worker_name,
            worker_shop_name=stakeholder.worker_shop_name,
            worker_branch_name=stakeholder.worker_branch_name,
            worker_role=stakeholder.worker_role,
            role_label=stakeholder.role_label or "",
            worker_email=stakeholder.worker_email,
            worker_phone=stakeholder.worker_phone,
            worker_shop_image=stakeholder.worker_shop_image,
            permissions=stakeholder.permissions or {},
            is_active=stakeholder.is_active,
            last_login=stakeholder.last_login,
            created_at=stakeholder.created_at,
            updated_at=stakeholder.updated_at,
        )
    }


@router.get("/me", response_model=StakeholderResponse)
async def get_me(user=Depends(get_current_user)):
    """Fetch the currently logged-in worker's latest profile and live permissions directly from the database"""
    return await get_stakeholder_by_id(user.get("sub"))


