from fastapi import APIRouter, Depends, Request
from model.Stakeholder import Stakeholder
from middleware.auth import get_current_stakeholder, require_roles
from schema.branch import BranchCreate, BranchUpdate, BranchResponse
from repository.branch import BranchService

branch_router = APIRouter(prefix="/api/v1/branches", tags=["Branches"])


@branch_router.post("", response_model=BranchResponse)
async def create_branch(
    payload: BranchCreate,
    current_user: Stakeholder = Depends(require_roles(["owner", "admin", "manager"]))
):
    branch = await BranchService.create_branch(
        payload=payload,
        shop_name=current_user.worker_shop_name,
        user_name=current_user.worker_name
    )
    return BranchResponse(
        id=str(branch.id),
        shop_name=branch.shop_name,
        branch_name=branch.branch_name,
        location=branch.location,
        phone=branch.phone,
        is_main=branch.is_main,
        is_active=branch.is_active
    )


@branch_router.get("", response_model=list[BranchResponse])
async def list_branches(
    current_user: Stakeholder = Depends(get_current_stakeholder)
):
    branches = await BranchService.get_shop_branches(current_user.worker_shop_name)
    return [
        BranchResponse(
            id=str(b.id),
            shop_name=b.shop_name,
            branch_name=b.branch_name,
            location=b.location,
            phone=b.phone,
            is_main=b.is_main,
            is_active=b.is_active
        )
        for b in branches
    ]


@branch_router.patch("/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: str,
    payload: BranchUpdate,
    current_user: Stakeholder = Depends(require_roles(["owner", "admin", "manager"]))
):
    branch = await BranchService.update_branch(branch_id, payload, current_user.worker_shop_name)
    return BranchResponse(
        id=str(branch.id),
        shop_name=branch.shop_name,
        branch_name=branch.branch_name,
        location=branch.location,
        phone=branch.phone,
        is_main=branch.is_main,
        is_active=branch.is_active
    )


@branch_router.delete("/{branch_id}")
async def delete_branch(
    branch_id: str,
    current_user: Stakeholder = Depends(require_roles(["owner", "admin"]))
):
    return await BranchService.delete_branch(branch_id, current_user.worker_shop_name)
