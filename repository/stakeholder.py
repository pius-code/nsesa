from utils.hasher import hashPwd
from fastapi import HTTPException
from model.Stakeholder import Stakeholder
from model.Shop import Shop
from model.Branch import Branch
from model.Inventory import Inventory
from model.Transaction import Transaction
from schema.stakeholder import (
    StakeholderCreate, adminStakeholderCreateWorker, StakeholderUpdate,
    StakeholderResponse, ShopImageUpdate, WorkerPermissionsUpdate,
    admin_permissions, worker_default_permissions, ProfileUpdateRequest,
) # noqa
from beanie.operators import In
from beanie import PydanticObjectId
from datetime import datetime, timezone


def _to_response(w: Stakeholder) -> StakeholderResponse:
    return StakeholderResponse(
        id=str(w.id),
        worker_name=w.worker_name,
        worker_shop_name=w.worker_shop_name,
        worker_branch_name=w.worker_branch_name,
        worker_role=w.worker_role,
        role_label=w.role_label or "",
        worker_email=w.worker_email,
        worker_phone=w.worker_phone,
        worker_shop_image=w.worker_shop_image,
        permissions=w.permissions or {},
        is_active=w.is_active,
        last_login=w.last_login,
        created_at=w.created_at,
        updated_at=w.updated_at,
    )


async def create_stakeholder(payload: StakeholderCreate):
    existing_email = await Stakeholder.find_one(Stakeholder.worker_email == payload.worker_email) # noqa
    if existing_email:
        raise HTTPException(status_code=400, detail="Invalid!, try changing the email") # noqa

    if payload.worker_role == "admin":
        existing_shop = await Stakeholder.find_one(Stakeholder.worker_shop_name == payload.worker_shop_name) # noqa
        if existing_shop:
            raise HTTPException(status_code=400, detail="A shop with this name already exists") # noqa

    new_worker = Stakeholder(
        worker_name=payload.worker_name,
        worker_shop_name=payload.worker_shop_name,
        worker_branch_name=payload.worker_branch_name,
        worker_role=payload.worker_role,
        worker_email=payload.worker_email,
        worker_phone=payload.worker_phone,
        worker_hashed_password=hashPwd(payload.worker_password),
        worker_shop_image=payload.worker_shop_image,
    )
    await new_worker.insert()

    if payload.worker_role == "admin":
        existing_shop_doc = await Shop.find_one(Shop.name == payload.worker_shop_name) # noqa
        if not existing_shop_doc:
            await Shop(name=payload.worker_shop_name).insert()

    return {
        "message": "Worker created successfully",
        "worker": str(new_worker.id),
    }


async def create_worker_by_admin(payload: adminStakeholderCreateWorker, admin: str): # noqa
    existing = await Stakeholder.find_one(Stakeholder.worker_email == payload.worker_email) # noqa
    worker_admin = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(admin)) # noqa
    if not worker_admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    if existing:
        raise HTTPException(status_code=400, detail="Invalid!, try changing the email!") # noqa
    if worker_admin.worker_role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Only admins can create workers") # noqa
    branch_name = payload.worker_branch_name.strip() if payload.worker_branch_name else worker_admin.worker_branch_name
    # Use provided permissions or default worker permissions
    perms = payload.permissions.model_dump() if payload.permissions else worker_default_permissions()
    new_worker = Stakeholder(
        worker_name=payload.worker_name,
        worker_shop_name=worker_admin.worker_shop_name,
        worker_branch_name=branch_name,
        worker_role="worker",  # all workers created via admin are always "worker" role
        role_label=payload.role_label or "",
        worker_email=payload.worker_email,
        worker_phone=payload.worker_phone,
        worker_hashed_password=hashPwd(payload.worker_password),
        worker_shop_image=worker_admin.worker_shop_image,
        permissions=perms,
    )
    await new_worker.insert()
    return {
        "message": "Worker created successfully",
        "worker": _to_response(new_worker),
    }


async def update_worker_permissions(worker_id: str, admin_id: str, payload: WorkerPermissionsUpdate):
    """Update permissions (and optionally role_label) for a specific worker. Admin-only."""
    admin = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(admin_id))
    if not admin:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if str(admin_id) == str(worker_id):
        raise HTTPException(status_code=400, detail="You cannot change your own permissions")

    worker = await Stakeholder.get(PydanticObjectId(worker_id))
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Shop isolation — admin can only modify workers within their own shop
    if admin.worker_role != "super_admin" and worker.worker_shop_name != admin.worker_shop_name:
        raise HTTPException(status_code=403, detail="Worker does not belong to your shop")

    # Admins cannot elevate to super_admin level — super_admin check is separate
    if worker.worker_role in ("admin", "super_admin") and admin.worker_role != "super_admin":
        raise HTTPException(status_code=403, detail="Cannot modify another admin's permissions")

    worker.permissions = payload.permissions.model_dump()
    if payload.role_label is not None:
        worker.role_label = payload.role_label
    await worker.save()
    return {
        "message": f"Permissions updated for '{worker.worker_name}'",
        "worker": _to_response(worker),
    }


async def migrate_permissions():
    """
    One-time migration: assign default permissions to existing workers who have
    no permissions set yet. Admins get all permissions; workers get can_sell only.
    Safe to run multiple times — skips workers that already have permissions.
    """
    all_workers = await Stakeholder.find_all().to_list()
    migrated = 0
    for w in all_workers:
        if w.permissions:  # already has permissions — skip
            continue
        if w.worker_role in ("admin", "super_admin"):
            w.permissions = admin_permissions()
        else:
            w.permissions = worker_default_permissions()
        await w.save()
        migrated += 1
    return {"message": f"Migration complete. {migrated} workers updated."}


async def get_workers_by_shop(shop_name: str):
    workers = await Stakeholder.find(Stakeholder.worker_shop_name == shop_name).to_list() # noqa
    return [_to_response(w) for w in workers]


async def get_all_stakeholders():
    workers = await Stakeholder.find_all().to_list()
    return [_to_response(w) for w in workers]


async def get_stakeholder_by_id(worker_id: str):
    worker = await Stakeholder.get(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return _to_response(worker)


async def update_shop_image(admin_id: str, payload: ShopImageUpdate):
    worker = await Stakeholder.get(PydanticObjectId(admin_id))
    if not worker:
        raise HTTPException(status_code=404, detail="Admin not found")
    worker.worker_shop_image = payload.worker_shop_image
    await worker.save()

    # Sync worker_shop_image to all workers in this shop
    await Stakeholder.find(
        Stakeholder.worker_shop_name == worker.worker_shop_name
    ).set({Stakeholder.worker_shop_image: payload.worker_shop_image})

    return {"message": "Shop image updated successfully"}


async def update_stakeholder(worker_id: str, payload: StakeholderUpdate):
    worker = await Stakeholder.get(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(worker, field, value)

    await worker.save()
    return {"message": "Worker updated successfully"}


async def deactivate_stakeholder(worker_id: str):
    worker = await Stakeholder.get(PydanticObjectId(worker_id))
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    worker.is_active = False
    await worker.save()
    return {"message": "Worker deactivated successfully"}


async def toggle_worker_status(worker_id: str, admin_id: str):
    if str(worker_id) == str(admin_id):
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    admin = await Stakeholder.get(PydanticObjectId(admin_id))
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    worker = await Stakeholder.get(PydanticObjectId(worker_id))
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    if admin.worker_role != "super_admin" and worker.worker_shop_name != admin.worker_shop_name:
        raise HTTPException(status_code=403, detail="You do not have permission to modify this worker")

    worker.is_active = not worker.is_active
    await worker.save()
    status_label = "activated" if worker.is_active else "deactivated"
    return {
        "message": f"Worker account {status_label} successfully",
        "is_active": worker.is_active,
    }


async def delete_worker_by_admin(worker_id: str, admin_id: str):
    if str(worker_id) == str(admin_id):
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    admin = await Stakeholder.get(PydanticObjectId(admin_id))
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    worker = await Stakeholder.get(PydanticObjectId(worker_id))
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    if admin.worker_role != "super_admin" and worker.worker_shop_name != admin.worker_shop_name:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this worker")

    await worker.delete()
    return {"message": "Worker account deleted successfully"}


async def get_Stakeholder_by_email(email: str):
    return await Stakeholder.find_one(Stakeholder.worker_email == email)


async def get_stakeholder_hashed_password(email: str) -> str | None:
    stakeholder = await Stakeholder.find_one(Stakeholder.worker_email == email)
    if stakeholder:
        return stakeholder.worker_hashed_password
    return None


async def get_stakeholder_worker_shop_name(id: str) -> str | None:
    stakeholder = await Stakeholder.get(PydanticObjectId(id))
    if stakeholder:
        return stakeholder.worker_shop_name
    return None


async def get_all_shops(page: int = 1, limit: int = 10):
    all_admins = await Stakeholder.find(
        In(Stakeholder.worker_role, ["admin", "super_admin"])
    ).sort(Stakeholder.created_at).to_list()

    # deduplicate by shop name — keep the earliest admin per shop
    seen = set()
    unique_admins = []
    for admin in all_admins:
        if admin.worker_shop_name not in seen:
            seen.add(admin.worker_shop_name)
            unique_admins.append(admin)

    total_shops = len(unique_admins)
    skip = (page - 1) * limit
    paginated = unique_admins[skip: skip + limit]

    shops = []
    for admin in paginated:
        worker_count = await Stakeholder.find(
            Stakeholder.worker_shop_name == admin.worker_shop_name,
            Stakeholder.worker_role == "worker",
        ).count()
        branch_count = await Branch.find(
            Branch.shop_name == admin.worker_shop_name,
            Branch.is_active == True,
        ).count()
        shop_doc = await Shop.find_one(Shop.name == admin.worker_shop_name)
        shops.append({
            "shop_name": admin.worker_shop_name,
            "shop_image": admin.worker_shop_image,
            "admin_name": admin.worker_name,
            "admin_email": admin.worker_email,
            "admin_phone": admin.worker_phone,
            "worker_count": worker_count,
            "branch_count": branch_count,
            "sms_sent_count": shop_doc.sms_sent_count if shop_doc else 0,
            "created_at": admin.created_at,
            "status": shop_doc.status if shop_doc else "active",
            "status_reason": shop_doc.status_reason if shop_doc else None,
        })

    return {
        "total_shops": total_shops,
        "page": page,
        "limit": limit,
        "total_pages": -(-total_shops // limit),
        "shops": shops,
    }


async def get_shop_details_for_super_admin(shop_name: str) -> dict:
    shop_doc = await Shop.find_one(Shop.name == shop_name)
    admin = await Stakeholder.find_one(
        Stakeholder.worker_shop_name == shop_name,
        In(Stakeholder.worker_role, ["admin", "super_admin"]),
    )
    if not admin:
        raise HTTPException(status_code=404, detail="Shop not found")

    branches = await Branch.find(
        Branch.shop_name == shop_name,
        Branch.is_active == True,
    ).sort(-Branch.is_main, Branch.branch_name).to_list()

    branch_details = []
    for b in branches:
        w_count = await Stakeholder.find(
            Stakeholder.worker_shop_name == shop_name,
            Stakeholder.worker_branch_name == b.branch_name,
            Stakeholder.is_active == True,
        ).count()
        inv_count = await Inventory.find(
            Inventory.worker_shop_name == shop_name,
            Inventory.branch_name == b.branch_name,
            Inventory.is_deleted == False,
        ).count()
        # Sum sales volume for this branch
        tx_sum_pipeline = [
            {"$match": {"at_shop": shop_name, "branch_name": b.branch_name, "status": "success", "$or": [{"is_deleted": False}, {"is_deleted": None}]}},
            {"$group": {"_id": None, "total": {"$sum": "$total_price"}}}
        ]
        tx_res = await Transaction.get_pymongo_collection().aggregate(tx_sum_pipeline).to_list(1)
        sales_vol = tx_res[0]["total"] if tx_res else 0.0

        branch_details.append({
            "id": str(b.id),
            "branch_name": b.branch_name,
            "location": b.location,
            "phone": b.phone,
            "is_main": b.is_main,
            "worker_count": w_count,
            "inventory_count": inv_count,
            "sales_volume": round(sales_vol, 2),
        })

    workers = await Stakeholder.find(
        Stakeholder.worker_shop_name == shop_name,
    ).sort(Stakeholder.worker_name).to_list()

    worker_list = [
        {
            "id": str(w.id),
            "worker_name": w.worker_name,
            "worker_email": w.worker_email,
            "worker_role": w.worker_role,
            "worker_branch_name": w.worker_branch_name,
            "worker_phone": w.worker_phone,
            "is_active": w.is_active,
        }
        for w in workers
    ]

    # Total shop revenue
    total_tx_pipeline = [
        {"$match": {"at_shop": shop_name, "status": "success", "$or": [{"is_deleted": False}, {"is_deleted": None}]}},
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}, "count": {"$sum": 1}}}
    ]
    tot_res = await Transaction.get_pymongo_collection().aggregate(total_tx_pipeline).to_list(1)
    tot_revenue = tot_res[0]["total"] if tot_res else 0.0
    tot_transactions = tot_res[0]["count"] if tot_res else 0

    return {
        "shop_name": shop_name,
        "shop_image": admin.worker_shop_image,
        "admin_name": admin.worker_name,
        "admin_email": admin.worker_email,
        "admin_phone": admin.worker_phone,
        "status": shop_doc.status if shop_doc else "active",
        "status_reason": shop_doc.status_reason if shop_doc else None,
        "sms_sent_count": shop_doc.sms_sent_count if shop_doc else 0,
        "total_revenue": round(tot_revenue, 2),
        "total_transactions": tot_transactions,
        "branches": branch_details,
        "workers": worker_list,
        "created_at": admin.created_at,
    }


async def toggle_worker_status(worker_id: str, admin_id: str):
    admin = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(admin_id))
    if not admin:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if str(admin.id) == str(worker_id):
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")

    worker = await Stakeholder.get(PydanticObjectId(worker_id))
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    if admin.worker_role != "super_admin" and worker.worker_shop_name != admin.worker_shop_name:
        raise HTTPException(status_code=403, detail="Worker does not belong to your shop")

    worker.is_active = not worker.is_active
    await worker.save()
    status_str = "activated" if worker.is_active else "deactivated"
    return {
        "message": f"Worker '{worker.worker_name}' has been {status_str}.",
        "worker": _to_response(worker),
    }


async def delete_worker_by_admin(worker_id: str, admin_id: str):
    admin = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(admin_id))
    if not admin:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if str(admin.id) == str(worker_id):
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")

    worker = await Stakeholder.get(PydanticObjectId(worker_id))
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    if admin.worker_role != "super_admin" and worker.worker_shop_name != admin.worker_shop_name:
        raise HTTPException(status_code=403, detail="Worker does not belong to your shop")

    if worker.worker_role in ("admin", "super_admin", "owner") and admin.worker_role != "super_admin":
        raise HTTPException(status_code=403, detail="Cannot delete an admin account.")

    await worker.delete()
    return {"message": f"Worker '{worker.worker_name}' removed successfully."}


async def update_worker_profile(worker_id: str, payload: ProfileUpdateRequest) -> StakeholderResponse:
    try:
        worker = await Stakeholder.get(PydanticObjectId(worker_id))
    except Exception:
        worker = await Stakeholder.get(worker_id)

    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    clean_phone = payload.worker_phone.strip() if payload.worker_phone else ""
    if not clean_phone:
        raise HTTPException(status_code=400, detail="Phone number is required.")

    worker.worker_phone = clean_phone

    if payload.worker_name and payload.worker_name.strip() != worker.worker_name:
        is_admin = worker.worker_role in ("admin", "super_admin")
        perms = worker.permissions or {}
        has_edit_perm = is_admin or perms.get("can_edit_profile", False)
        if not has_edit_perm:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to edit your name. Please contact your administrator."
            )
        worker.worker_name = payload.worker_name.strip()

    worker.updated_at = datetime.now(timezone.utc)
    await worker.save()
    return _to_response(worker)

