from fastapi import APIRouter, Depends
from model.Stakeholder import Stakeholder
from middleware.auth import get_current_stakeholder, require_roles
from schema.stock_movement import StockAdjustmentRequest, StockTransferRequest, BulkProductImportRequest
from repository.stock_movement import StockMovementService

stock_router = APIRouter(prefix="/api/v1/stock", tags=["Stock & Inventory Intelligence"])


@stock_router.post("/adjust")
async def adjust_stock(
    payload: StockAdjustmentRequest,
    current_user: Stakeholder = Depends(require_roles(["owner", "admin", "manager", "inventory_manager"]))
):
    return await StockMovementService.adjust_stock(
        payload=payload,
        shop_name=current_user.worker_shop_name,
        user_id=str(current_user.id),
        user_name=current_user.worker_name
    )


@stock_router.post("/transfer")
async def transfer_stock(
    payload: StockTransferRequest,
    current_user: Stakeholder = Depends(require_roles(["owner", "admin", "manager", "inventory_manager"]))
):
    return await StockMovementService.transfer_stock(
        payload=payload,
        shop_name=current_user.worker_shop_name,
        user_id=str(current_user.id),
        user_name=current_user.worker_name
    )


@stock_router.get("/intelligence")
async def get_low_stock_intelligence(
    current_user: Stakeholder = Depends(get_current_stakeholder)
):
    return await StockMovementService.get_low_stock_intelligence(current_user.worker_shop_name)


@stock_router.post("/bulk-import")
async def bulk_import(
    payload: BulkProductImportRequest,
    current_user: Stakeholder = Depends(require_roles(["owner", "admin", "manager", "inventory_manager"]))
):
    return await StockMovementService.bulk_import_products(
        payload=payload,
        shop_name=current_user.worker_shop_name,
        user_id=str(current_user.id),
        user_name=current_user.worker_name
    )


@stock_router.get("/movements")
async def get_movements(
    product_id: str | None = None,
    limit: int = 50,
    skip: int = 0,
    current_user: Stakeholder = Depends(get_current_stakeholder)
):
    return await StockMovementService.get_movement_history(
        shop_name=current_user.worker_shop_name,
        product_id=product_id,
        limit=limit,
        skip=skip
    )
