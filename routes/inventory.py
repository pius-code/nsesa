from middleware.auth import get_current_user
from fastapi import Depends, APIRouter
from repository.inventory import get_all_inventory_items_for_shop


router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


async def get_inventory_by_shop(shop_name: str):
    pass


@router.get("/get_my_shop_inventory")
async def get_inventory_by_worker(worker=Depends(get_current_user)):
    worker_id = worker.get("sub")
    return await get_all_inventory_items_for_shop(worker_id)
