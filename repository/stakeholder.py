from utils.hasher import hashPwd
from fastapi import HTTPException
from model.Stakeholder import Stakeholder
from schema.stakeholder import StakeholderCreate, StakeholderUpdate, StakeholderResponse


async def create_stakeholder(payload: StakeholderCreate):
    existing = await Stakeholder.find_one(Stakeholder.worker_email == payload.worker_email)
    if existing:
        raise HTTPException(status_code=400, detail="Worker with this email already exists")

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
        "worker_id": str(new_worker.id),
    }


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
