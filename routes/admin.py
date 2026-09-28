from fastapi import APIRouter, Depends, Query
from schema.inventory import InventoryCreate, InventoryUpdate
from repository.inventory import add_to_shop_inventory, update_inventory_item
from middleware.auth import admin_protected_route, super_admin_protected_route, get_current_user
from schema.stakeholder import adminStakeholderCreateWorker, ShopImageUpdate
from schema.shop import ShopProfileUpdate
from repository.shop import get_shop_profile, update_shop_profile
from repository.stakeholder import (
    create_worker_by_admin,
    get_workers_by_shop,
    get_stakeholder_worker_shop_name,
    update_shop_image,
    get_all_shops,
    get_shop_details_for_super_admin,
    toggle_worker_status,
    delete_worker_by_admin,
)

router = APIRouter(prefix="/api/v1", tags=["admin"])


@router.post("/add_to_inventory")
async def add_to_inventory(payload: InventoryCreate, user=Depends(get_current_user)):  # noqa
    """Save a new inventory item to the database (admin or branch worker)"""
    user_id = str(user.get("sub"))
    return await add_to_shop_inventory(payload, user_id)  # type: ignore


@router.patch("/inventory/update_stock/{inventory_id}")
async def restock_inventory(inventory_id: str, payload: InventoryUpdate, user=Depends(get_current_user)):  # noqa
    """Update an inventory item — stock, price, name, SKU, and/or category""" # noqa
    user_id = str(user.get("sub"))
    return await update_inventory_item(inventory_id, payload, user_id)  # type: ignore # noqa


@router.post("/create_worker")
async def create_worker(payload: adminStakeholderCreateWorker, admin =Depends(admin_protected_route)):  # noqa
    """Create a new worker account"""
    return await create_worker_by_admin(payload, admin)  # type: ignore


@router.patch("/add_shop_image")
async def add_shop_image(payload: ShopImageUpdate, admin=Depends(admin_protected_route)):  # noqa
    """Update the shop image for the logged-in admin"""
    return await update_shop_image(admin, payload)


@router.get("/all_shops")
async def all_shops(
    super_admin=Depends(super_admin_protected_route),  # noqa
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
):
    """Super admin only — returns paginated shops with worker counts"""
    return await get_all_shops(page=page, limit=limit)


@router.get("/admin/shops/{shop_name}/details")
async def get_shop_details(
    shop_name: str,
    super_admin=Depends(super_admin_protected_route),
):
    """Super admin only — comprehensive details for a shop including branches, staff, and SMS usage"""
    return await get_shop_details_for_super_admin(shop_name)


@router.get("/shop_workers")
async def get_shop_workers(admin =Depends(admin_protected_route)): # noqa
    """Get all workers for the admin's shop"""
    shop_name = await get_stakeholder_worker_shop_name(admin)
    if not shop_name:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Shop not found for this admin") # noqa
    return await get_workers_by_shop(shop_name)


@router.patch("/workers/{worker_id}/toggle-status")
async def toggle_worker(worker_id: str, admin=Depends(admin_protected_route)):
    """Toggle worker active / inactive status"""
    return await toggle_worker_status(worker_id, admin)


@router.delete("/workers/{worker_id}")
async def delete_worker(worker_id: str, admin=Depends(admin_protected_route)):
    """Permanently delete a worker account from the shop"""
    return await delete_worker_by_admin(worker_id, admin)


@router.get("/shop/profile")
async def get_my_shop_profile(admin=Depends(admin_protected_route)):
    """Get the logged-in admin's shop profile"""
    shop_name = await get_stakeholder_worker_shop_name(admin)
    if not shop_name:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Shop not found for this admin")
    return await get_shop_profile(shop_name)


@router.patch("/shop/profile")
async def update_my_shop_profile(payload: ShopProfileUpdate, admin=Depends(admin_protected_route)):
    """Update shop profile (name, logo, location, phone, description) with cascade rename support"""
    shop_name = await get_stakeholder_worker_shop_name(admin)
    if not shop_name:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Shop not found for this admin")
    return await update_shop_profile(shop_name, payload)


