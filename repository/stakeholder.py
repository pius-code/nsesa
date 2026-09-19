from utils.hasher import hashPwd
from fastapi import HTTPException
from model.Stakeholder import Stakeholder
from model.Shop import Shop
from schema.stakeholder import StakeholderCreate, adminStakeholderCreateWorker, StakeholderUpdate, StakeholderResponse, ShopImageUpdate # noqa
from beanie.operators import In
from beanie import PydanticObjectId


def _to_response(w: Stakeholder) -> StakeholderResponse:
    return StakeholderResponse(
        id=str(w.id),
        worker_name=w.worker_name,
        worker_shop_name=w.worker_shop_name,
        worker_branch_name=w.worker_branch_name,
        worker_role=w.worker_role,
        worker_email=w.worker_email,
        worker_phone=w.worker_phone,
        worker_shop_image=w.worker_shop_image,
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
    new_worker = Stakeholder(
        worker_name=payload.worker_name,
        worker_shop_name=worker_admin.worker_shop_name,  # noqa
        worker_branch_name=worker_admin.worker_branch_name,  # noqa
        worker_role=payload.worker_role,
        worker_email=payload.worker_email,
        worker_phone=payload.worker_phone,
        worker_hashed_password=hashPwd(payload.worker_password),
        worker_shop_image=worker_admin.worker_shop_image,
    )
    await new_worker.insert()
    return {
        "message": "Worker created successfully",
        "worker": _to_response(new_worker),
    }


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
    worker = await Stakeholder.get(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    worker.is_active = False
    await worker.save()
    return {"message": "Worker deactivated successfully"}


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
        shop_doc = await Shop.find_one(Shop.name == admin.worker_shop_name)
        shops.append({
            "shop_name": admin.worker_shop_name,
            "shop_image": admin.worker_shop_image,
            "admin_name": admin.worker_name,
            "admin_email": admin.worker_email,
            "admin_phone": admin.worker_phone,
            "worker_count": worker_count,
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
