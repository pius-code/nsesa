from model.Branch import Branch
from model.Stakeholder import Stakeholder
from model.Inventory import Inventory
from schema.branch import BranchCreate, BranchUpdate, BranchResponse
from beanie import PydanticObjectId
from fastapi import HTTPException


async def _get_admin_shop(admin_id: str) -> str:
    admin = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(admin_id))
    if not admin:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return admin.worker_shop_name


async def create_branch(payload: BranchCreate, admin_id: str) -> BranchResponse:
    shop_name = await _get_admin_shop(admin_id)

    existing = await Branch.find_one(
        Branch.shop_name == shop_name,
        Branch.branch_name == payload.branch_name.strip(),
        Branch.is_active == True,
    )
    if existing:
        raise HTTPException(status_code=400, detail="A branch with this name already exists in your shop")

    # If this is marked as main, remove is_main from any other branch
    if payload.is_main:
        await Branch.find(Branch.shop_name == shop_name).set({Branch.is_main: False})

    # If this is the shop's first branch, automatically make it the main branch
    branch_count = await Branch.find(Branch.shop_name == shop_name, Branch.is_active == True).count()
    is_main = payload.is_main or (branch_count == 0)

    branch = Branch(
        shop_name=shop_name,
        branch_name=payload.branch_name.strip(),
        location=payload.location.strip() if payload.location else None,
        phone=payload.phone.strip() if payload.phone else None,
        is_main=is_main,
        is_active=True,
    )
    await branch.insert()

    return BranchResponse(
        id=str(branch.id),
        shop_name=branch.shop_name,
        branch_name=branch.branch_name,
        location=branch.location,
        phone=branch.phone,
        is_main=branch.is_main,
        is_active=branch.is_active,
        worker_count=0,
        inventory_count=0,
        created_at=branch.created_at,
        updated_at=branch.updated_at,
    )


async def get_shop_branches(shop_name: str) -> list[BranchResponse]:
    branches = await Branch.find(
        Branch.shop_name == shop_name,
        Branch.is_active == True,
    ).sort(-Branch.is_main, Branch.branch_name).to_list()

    responses = []
    for b in branches:
        workers = await Stakeholder.find(
            Stakeholder.worker_shop_name == shop_name,
            Stakeholder.worker_branch_name == b.branch_name,
            Stakeholder.is_active == True,
        ).count()

        inv = await Inventory.find(
            Inventory.worker_shop_name == shop_name,
            Inventory.branch_name == b.branch_name,
            Inventory.is_deleted == False,
        ).count()

        responses.append(
            BranchResponse(
                id=str(b.id),
                shop_name=b.shop_name,
                branch_name=b.branch_name,
                location=b.location,
                phone=b.phone,
                is_main=b.is_main,
                is_active=b.is_active,
                worker_count=workers,
                inventory_count=inv,
                created_at=b.created_at,
                updated_at=b.updated_at,
            )
        )
    return responses


async def update_branch(branch_id: str, payload: BranchUpdate, admin_id: str) -> BranchResponse:
    shop_name = await _get_admin_shop(admin_id)
    branch = await Branch.get(PydanticObjectId(branch_id))
    if not branch or branch.shop_name != shop_name:
        raise HTTPException(status_code=404, detail="Branch not found")

    update_data = payload.model_dump(exclude_none=True)

    if update_data.get("is_main") is True:
        await Branch.find(Branch.shop_name == shop_name).set({Branch.is_main: False})

    # If branch_name changed, rename it on associated workers and inventory
    old_name = branch.branch_name
    new_name = update_data.get("branch_name")
    if new_name and new_name.strip() != old_name:
        new_name = new_name.strip()
        update_data["branch_name"] = new_name
        # Update workers & inventory assigned to this branch
        await Stakeholder.find(
            Stakeholder.worker_shop_name == shop_name,
            Stakeholder.worker_branch_name == old_name,
        ).set({Stakeholder.worker_branch_name: new_name})

        await Inventory.find(
            Inventory.worker_shop_name == shop_name,
            Inventory.branch_name == old_name,
        ).set({Inventory.branch_name: new_name})

    for field, val in update_data.items():
        setattr(branch, field, val)

    await branch.save()

    workers = await Stakeholder.find(
        Stakeholder.worker_shop_name == shop_name,
        Stakeholder.worker_branch_name == branch.branch_name,
        Stakeholder.is_active == True,
    ).count()

    inv = await Inventory.find(
        Inventory.worker_shop_name == shop_name,
        Inventory.branch_name == branch.branch_name,
        Inventory.is_deleted == False,
    ).count()

    return BranchResponse(
        id=str(branch.id),
        shop_name=branch.shop_name,
        branch_name=branch.branch_name,
        location=branch.location,
        phone=branch.phone,
        is_main=branch.is_main,
        is_active=branch.is_active,
        worker_count=workers,
        inventory_count=inv,
        created_at=branch.created_at,
        updated_at=branch.updated_at,
    )


async def delete_branch(branch_id: str, admin_id: str):
    shop_name = await _get_admin_shop(admin_id)
    branch = await Branch.get(PydanticObjectId(branch_id))
    if not branch or branch.shop_name != shop_name:
        raise HTTPException(status_code=404, detail="Branch not found")

    branch.is_active = False
    await branch.save()
    return {"message": "Branch deactivated successfully"}
