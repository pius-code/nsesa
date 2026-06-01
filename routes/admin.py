from fastapi import APIRouter, Depends
from schema.inventory import InventoryCreate, InventoryUpdate
from repository.inventory import add_to_shop_inventory, update_stock
from middleware.auth import admin_protected_route
from schema.stakeholder import adminStakeholderCreateWorker, ShopImageUpdate
from repository.stakeholder import create_worker_by_admin, get_workers_by_shop, get_stakeholder_worker_shop_name, update_shop_image # noqa

router = APIRouter(prefix="/api/v1", tags=["admin"])


@router.post("/add_to_inventory")
async def add_to_inventory(payload: InventoryCreate, admin =Depends(admin_protected_route)):  # noqa
    """Save a new inventory item to the database"""
    return await add_to_shop_inventory(payload, admin)  # type: ignore


@router.patch("/inventory/update_stock/{inventory_id}")
async def restock_inventory(inventory_id: str, payload: InventoryUpdate, admin=Depends(admin_protected_route)):  # noqa
    """Update stock amount for an inventory item"""
    return await update_stock(inventory_id, payload.amount_available, admin)  # type: ignore # noqa


@router.post("/create_worker")
async def create_worker(payload: adminStakeholderCreateWorker, admin =Depends(admin_protected_route)):  # noqa
    """Create a new worker account"""
    return await create_worker_by_admin(payload, admin)  # type: ignore


@router.patch("/add_shop_image")
async def add_shop_image(payload: ShopImageUpdate, admin=Depends(admin_protected_route)):  # noqa
    """Update the shop image for the logged-in admin"""
    return await update_shop_image(admin, payload)


@router.get("/shop_workers")
async def get_shop_workers(admin =Depends(admin_protected_route)): # noqa
    """Get all workers for the admin's shop"""
    shop_name = await get_stakeholder_worker_shop_name(admin)
    if not shop_name:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Shop not found for this admin") # noqa
    return await get_workers_by_shop(shop_name)
