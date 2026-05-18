from fastapi import APIRouter, Depends
from schema.inventory import InventoryCreate
from repository.inventory import add_to_shop_inventory
from middleware.auth import admin_protected_route
from schema.stakeholder import adminStakeholderCreateWorker
from repository.stakeholder import create_worker_by_admin, get_workers_by_shop, get_stakeholder_worker_shop_name # noqa

router = APIRouter(prefix="/api/v1", tags=["admin"])


@router.post("/add_to_inventory")
async def add_to_inventory(payload: InventoryCreate, admin =Depends(admin_protected_route)):  # noqa
    """Save a new inventory item to the database"""
    return await add_to_shop_inventory(payload, admin)  # type: ignore


@router.post("/create_worker")
async def create_worker(payload: adminStakeholderCreateWorker, admin =Depends(admin_protected_route)):  # noqa
    """Create a new worker account"""
    return await create_worker_by_admin(payload, admin)  # type: ignore


@router.get("/shop_workers")
async def get_shop_workers(admin =Depends(admin_protected_route)): # noqa
    """Get all workers for the admin's shop"""
    shop_name = await get_stakeholder_worker_shop_name(admin)
    if not shop_name:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Shop not found for this admin") # noqa
    return await get_workers_by_shop(shop_name)
