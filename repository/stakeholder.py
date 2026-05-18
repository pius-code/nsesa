from utils.hasher import hashPwd
from fastapi import HTTPException
from model.Stakeholder import Stakeholder
from schema.stakeholder import StakeholderCreate, adminStakeholderCreateWorker, StakeholderUpdate, StakeholderResponse # noqa
from beanie import PydanticObjectId


async def create_stakeholder(payload: StakeholderCreate):
    existing_email = await Stakeholder.find_one(Stakeholder.worker_email == payload.worker_email) # noqa
    if existing_email:
        raise HTTPException(status_code=400, detail="Worker with this email already exists") # noqa

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
        worker_hashed_password=hashPwd(payload.worker_password),
    )
    await new_worker.insert()
    return {
        "message": "Worker created successfully",
        "worker": str(new_worker.id),
    }


async def create_worker_by_admin(payload: adminStakeholderCreateWorker, admin: str): # noqa
    print(admin) # noqa
    existing = await Stakeholder.find_one(Stakeholder.worker_email == payload.worker_email) # noqa
    worker_admin = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(admin)) # noqa
    if not worker_admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    if existing:
        raise HTTPException(status_code=400, detail="Worker with this email already exists") # noqa
    if worker_admin.worker_role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create workers") # noqa
    new_worker = Stakeholder(
        worker_name=payload.worker_name,
        worker_shop_name=worker_admin.worker_shop_name, # noqa
        worker_branch_name=worker_admin.worker_branch_name, # noqa
        worker_role=payload.worker_role,
        worker_email=payload.worker_email,
        worker_hashed_password=hashPwd(payload.worker_password),
    )
    await new_worker.insert()
    return {
        "message": "Worker created successfully",
        "worker": StakeholderResponse(
            id=str(new_worker.id),
            worker_name=new_worker.worker_name,
            worker_shop_name=new_worker.worker_shop_name,
            worker_branch_name=new_worker.worker_branch_name,
            worker_role=new_worker.worker_role,
            worker_email=new_worker.worker_email,
            is_active=new_worker.is_active,
            last_login=new_worker.last_login,
            created_at=new_worker.created_at,
            updated_at=new_worker.updated_at,
        )
    }


async def get_workers_by_shop(shop_name: str):
    workers = await Stakeholder.find(Stakeholder.worker_shop_name == shop_name).to_list() # noqa
    return [
        StakeholderResponse(
            id=str(w.id),
            worker_name=w.worker_name,
            worker_shop_name=w.worker_shop_name,
            worker_branch_name=w.worker_branch_name,
            worker_role=w.worker_role,
            worker_email=w.worker_email,
            is_active=w.is_active,
            last_login=w.last_login,
            created_at=w.created_at,
            updated_at=w.updated_at,
        )
        for w in workers
    ]


async def get_all_stakeholders():
    workers = await Stakeholder.find_all().to_list()
    return [
        StakeholderResponse(
            id=str(w.id),
            worker_name=w.worker_name,
            worker_shop_name=w.worker_shop_name,
            worker_branch_name=w.worker_branch_name,
            worker_role=w.worker_role,
            worker_email=w.worker_email,
            is_active=w.is_active,
            last_login=w.last_login,
            created_at=w.created_at,
            updated_at=w.updated_at,
        )
        for w in workers
    ]


async def get_stakeholder_by_id(worker_id: str):
    worker = await Stakeholder.get(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return StakeholderResponse(
        id=str(worker.id),
        worker_name=worker.worker_name,
        worker_shop_name=worker.worker_shop_name,
        worker_branch_name=worker.worker_branch_name,
        worker_role=worker.worker_role,
        worker_email=worker.worker_email,
        is_active=worker.is_active,
        last_login=worker.last_login,
        created_at=worker.created_at,
        updated_at=worker.updated_at,
    )


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
