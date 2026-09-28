from middleware.auth import get_current_user, admin_protected_route
from fastapi import Depends, APIRouter, UploadFile, File, Query
from schema.inventory import InventoryRestockRequest, InventoryUpdate
from repository.inventory import (
    get_all_inventory_items_for_shop,
    bulk_import_inventory,
    delete_inventory_item,
    restock_inventory_item,
    get_product_stock_logs,
    update_inventory_item,
)

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.get("/get_my_shop_inventory")
async def get_inventory_by_worker(
    branch_name: str | None = Query(default=None, description="Optional branch filter for admin"),
    worker=Depends(get_current_user),
):
    worker_id = worker.get("sub")
    return await get_all_inventory_items_for_shop(worker_id, branch_name=branch_name)


@router.post("/bulk_import")
async def bulk_import(file: UploadFile = File(...), admin=Depends(admin_protected_route)):
    """Admin only — bulk add products from a CSV file (product_name, product_price, amount_available, sku, category)"""
    contents = await file.read()
    return await bulk_import_inventory(contents, admin)


@router.post("/{inventory_id}/restock")
async def restock_item(
    inventory_id: str,
    payload: InventoryRestockRequest,
    admin=Depends(admin_protected_route),
):
    """Admin/Worker — Add quantity to existing stock and log immutable audit trail"""
    return await restock_inventory_item(inventory_id, payload, admin)


@router.get("/{inventory_id}/logs")
async def get_stock_logs(
    inventory_id: str,
    admin=Depends(admin_protected_route),
):
    """Get complete immutable stock ledger history for a specific product"""
    return await get_product_stock_logs(inventory_id, admin)


@router.patch("/update_stock/{inventory_id}")
async def update_item_details(
    inventory_id: str,
    payload: InventoryUpdate,
    admin=Depends(admin_protected_route),
):
    """Admin only — Update product metadata (name, price, cost price, category, supplier, SKU)"""
    return await update_inventory_item(inventory_id, payload, admin)


@router.delete("/{inventory_id}")
async def remove_inventory_item(inventory_id: str, admin=Depends(admin_protected_route)):
    """Admin only — soft delete an inventory item"""
    return await delete_inventory_item(inventory_id, admin)
