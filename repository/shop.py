# repository/shop.py
from model.Shop import Shop
from datetime import datetime, timezone
from fastapi import HTTPException


async def get_shop_status(shop_name: str) -> Shop | None:
    return await Shop.find_one(Shop.name == shop_name)


async def _set_shop_status(shop_name: str, status: str, reason: str, changed_by: str): # noqa
    shop = await Shop.find_one(Shop.name == shop_name)
    if not shop:
        # Backfill for shops that predate the Shop collection
        shop = Shop(name=shop_name)
    shop.status = status
    shop.status_reason = reason
    shop.status_changed_by = changed_by
    shop.status_changed_at = datetime.now(timezone.utc)
    await shop.save()
    return {"message": f"Shop {status} successfully"}


async def suspend_shop(shop_name: str, reason: str, super_admin_id: str):
    return await _set_shop_status(shop_name, "suspended", reason, super_admin_id) # noqa


async def delete_shop(shop_name: str, reason: str, super_admin_id: str):
    return await _set_shop_status(shop_name, "deleted", reason, super_admin_id)


async def reactivate_shop(shop_name: str, super_admin_id: str):
    shop = await Shop.find_one(Shop.name == shop_name)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    shop.status = "active"
    shop.status_reason = None
    shop.status_changed_by = super_admin_id
    shop.status_changed_at = datetime.now(timezone.utc)
    await shop.save()
    return {"message": "Shop reactivated successfully"}
