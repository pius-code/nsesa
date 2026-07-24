from middleware.auth import get_current_user, admin_protected_route
from fastapi import Depends, APIRouter, UploadFile, File
from repository.inventory import get_all_inventory_items_for_shop, bulk_import_inventory, delete_inventory_item # noqa


router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.get("/get_my_shop_inventory")
async def get_inventory_by_worker(worker=Depends(get_current_user)):
    worker_id = worker.get("sub")
    return await get_all_inventory_items_for_shop(worker_id)


@router.post("/bulk_import")
async def bulk_import(file: UploadFile = File(...), admin=Depends(admin_protected_route)): # noqa
    """Admin only — bulk add products from a CSV file (product_name, product_price, amount_available, sku, category)""" # noqa
    contents = await file.read()
    return await bulk_import_inventory(contents, admin)


@router.delete("/{inventory_id}")
async def remove_inventory_item(inventory_id: str, admin=Depends(admin_protected_route)): # noqa
    """Admin only — soft delete an inventory item"""
    return await delete_inventory_item(inventory_id, admin)
