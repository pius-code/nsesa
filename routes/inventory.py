from middleware.auth import get_current_user, require_permission, require_any_permission
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
    worker_id: str = Depends(require_any_permission("can_sell", "can_add_inventory", "can_update_stock", "can_manage_orders")),
):
    return await get_all_inventory_items_for_shop(worker_id, branch_name=branch_name)


@router.post("/bulk_import")
async def bulk_import(file: UploadFile = File(...), worker_id=Depends(require_permission("can_add_inventory"))):
    """Permission: can_add_inventory — bulk add products from a CSV file"""
    contents = await file.read()
    return await bulk_import_inventory(contents, worker_id)


@router.post("/{inventory_id}/restock")
async def restock_item(
    inventory_id: str,
    payload: InventoryRestockRequest,
    worker_id=Depends(require_permission("can_update_stock")),
):
    """Permission: can_update_stock — Add quantity to existing stock and log immutable audit trail"""
    return await restock_inventory_item(inventory_id, payload, worker_id)


@router.get("/{inventory_id}/logs")
async def get_stock_logs(
    inventory_id: str,
    worker_id=Depends(require_permission("can_add_inventory")),
):
    """Get complete immutable stock ledger history for a specific product"""
    return await get_product_stock_logs(inventory_id, worker_id)


@router.patch("/update_stock/{inventory_id}")
async def update_item_details(
    inventory_id: str,
    payload: InventoryUpdate,
    worker_id=Depends(require_permission("can_add_inventory")),
):
    """Permission: can_add_inventory — Update product metadata (name, price, cost price, category, supplier, SKU)"""
    return await update_inventory_item(inventory_id, payload, worker_id)


@router.delete("/{inventory_id}")
async def remove_inventory_item(inventory_id: str, worker_id=Depends(require_permission("can_add_inventory"))):
    """Permission: can_add_inventory — soft delete an inventory item"""
    return await delete_inventory_item(inventory_id, worker_id)
