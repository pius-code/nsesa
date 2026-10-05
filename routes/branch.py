from fastapi import APIRouter, Depends
from schema.branch import BranchCreate, BranchUpdate, BranchResponse, SwitchBranchRequest
from repository.branch import (
    create_branch,
    get_shop_branches,
    update_branch,
    delete_branch,
    switch_active_branch,
)
from repository.stakeholder import get_stakeholder_worker_shop_name
from middleware.auth import get_current_user, require_any_permission

router = APIRouter(prefix="/api/v1/branches", tags=["branches"])


@router.post("/switch")
async def switch_branch(
    payload: SwitchBranchRequest,
    user: dict = Depends(get_current_user),
):
    """Switch active operating branch context for the current session"""
    return await switch_active_branch(user.get("sub"), payload.branch_name)


@router.post("", response_model=BranchResponse)
async def add_branch(
    payload: BranchCreate,
    admin_id: str = Depends(require_any_permission("can_manage_branches")),
):
    """Create a new branch for the shop"""
    return await create_branch(payload, admin_id)


@router.get("", response_model=list[BranchResponse])
async def list_branches(user: dict = Depends(get_current_user)):
    """Any authenticated user — list all branches for their shop"""
    shop_name = await get_stakeholder_worker_shop_name(user.get("sub"))
    if not shop_name:
        return []
    return await get_shop_branches(shop_name)


@router.patch("/{branch_id}", response_model=BranchResponse)
async def edit_branch(
    branch_id: str,
    payload: BranchUpdate,
    admin_id: str = Depends(require_any_permission("can_manage_branches")),
):
    """Update branch information"""
    return await update_branch(branch_id, payload, admin_id)


@router.delete("/{branch_id}")
async def remove_branch(
    branch_id: str,
    admin_id: str = Depends(require_any_permission("can_manage_branches")),
):
    """Deactivate a branch"""
    return await delete_branch(branch_id, admin_id)

