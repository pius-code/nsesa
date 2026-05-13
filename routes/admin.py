from fastapi import APIRouter, Depends
from schema.inventory import InventoryCreate
from repository.inventory import add_to_shop_inventory
from middleware.auth import admin_protected_route
from schema.stakeholder import adminStakeholderCreateWorker
from repository.stakeholder import create_worker_by_admin

router = APIRouter(prefix="/api/v1", tags=["admin"])


@router.post("/add_to_inventory")
async def add_to_inventory(payload: InventoryCreate, admin =Depends(admin_protected_route)):  # noqa
    """Save a new inventory item to the database"""
    return await add_to_shop_inventory(payload, admin)  # type: ignore


@router.post("/create_worker")
async def create_worker(payload: adminStakeholderCreateWorker, admin =Depends(admin_protected_route)):  # noqa
    """Create a new worker account"""
    return await create_worker_by_admin(payload, admin)  # type: ignore
