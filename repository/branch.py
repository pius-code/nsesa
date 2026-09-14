from fastapi import HTTPException
from beanie import PydanticObjectId
from model.Branch import Branch
from model.Subscription import Subscription
from schema.branch import BranchCreate, BranchUpdate, BranchResponse


class BranchService:
    @staticmethod
    async def create_branch(payload: BranchCreate, shop_name: str, user_name: str) -> Branch:
        # Check subscription branch limit
        sub = await Subscription.find_one(Subscription.shop_name == shop_name)
        max_branches = sub.max_branches if sub else 1

        current_count = await Branch.find(
            Branch.shop_name == shop_name,
            Branch.is_active == True
        ).count()

        if current_count >= max_branches:
            raise HTTPException(
                status_code=403,
                detail=f"Branch limit reached for your current plan ({current_count}/{max_branches}). Please upgrade to add more branches."
            )

        existing = await Branch.find_one(
            Branch.shop_name == shop_name,
            Branch.branch_name == payload.branch_name,
            Branch.is_active == True
        )
        if existing:
            raise HTTPException(status_code=400, detail="A branch with this name already exists.")

        branch = Branch(
            business_id=shop_name,
            shop_name=shop_name,
            branch_name=payload.branch_name,
            location=payload.location,
            phone=payload.phone,
            is_main=payload.is_main or (current_count == 0),
            is_active=True,
            created_by=user_name,
        )
        await branch.insert()
        return branch

    @staticmethod
    async def get_shop_branches(shop_name: str) -> list[Branch]:
        branches = await Branch.find(
            Branch.shop_name == shop_name,
            Branch.is_active == True
        ).to_list()

        # Ensure at least Main Branch exists if none are saved
        if not branches:
            default_branch = Branch(
                business_id=shop_name,
                shop_name=shop_name,
                branch_name="Main Branch",
                location="Main Location",
                is_main=True,
                is_active=True,
                created_by="system",
            )
            await default_branch.insert()
            branches = [default_branch]

        return branches

    @staticmethod
    async def update_branch(branch_id: str, payload: BranchUpdate, shop_name: str) -> Branch:
        try:
            branch = await Branch.get(PydanticObjectId(branch_id))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid branch ID")

        if not branch or branch.shop_name != shop_name:
            raise HTTPException(status_code=404, detail="Branch not found")

        if payload.branch_name is not None:
            branch.branch_name = payload.branch_name
        if payload.location is not None:
            branch.location = payload.location
        if payload.phone is not None:
            branch.phone = payload.phone
        if payload.is_main is not None:
            if payload.is_main:
                # Unmark previous main branch
                await Branch.find(
                    Branch.shop_name == shop_name,
                    Branch.is_main == True
                ).update({"$set": {Branch.is_main: False}})
            branch.is_main = payload.is_main
        if payload.is_active is not None:
            branch.is_active = payload.is_active

        await branch.save()
        return branch

    @staticmethod
    async def delete_branch(branch_id: str, shop_name: str) -> dict:
        try:
            branch = await Branch.get(PydanticObjectId(branch_id))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid branch ID")

        if not branch or branch.shop_name != shop_name:
            raise HTTPException(status_code=404, detail="Branch not found")

        if branch.is_main:
            raise HTTPException(status_code=400, detail="Cannot delete the main branch of your business.")

        branch.is_active = False
        await branch.save()
        return {"message": f"Branch '{branch.branch_name}' deactivated successfully."}
