from fastapi import APIRouter, HTTPException
from schema.stakeholder import StakeholderCreate, StakeholderLogin , StakeholderResponse
from repository.stakeholder import create_stakeholder, get_Stakeholder_by_email, get_stakeholder_hashed_password
from utils.hasher import verifyPwd
from helpers.auth import generate_token

router = APIRouter(prefix="/api/v1", tags=["stakeholder"])


@router.post("/registerme")
async def register_stakeholder(
    payload: StakeholderCreate,
):  # noqa
    """Register a new stakeholder account"""
    return await create_stakeholder(payload)  # type: ignore



@router.post("/login")
async def login_stakeholder(payload: StakeholderLogin):
    """Login stakeholder and return JWT token"""
    stakeholder = await get_Stakeholder_by_email(payload.worker_email)
    if not stakeholder:
        raise HTTPException(status_code=404, detail="Stakeholder not found")
    hashed_password = await get_stakeholder_hashed_password(payload.worker_email)
    if not verifyPwd(payload.worker_password, str(hashed_password)):
        raise HTTPException(status_code=401, detail="Invalid credentials")
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
            worker_email=stakeholder.worker_email,
            is_active=stakeholder.is_active,
            last_login=stakeholder.last_login,
            created_at=stakeholder.created_at,
            updated_at=stakeholder.updated_at,
        )
    }

