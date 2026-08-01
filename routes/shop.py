from fastapi import APIRouter, Depends
from schema.shop import ShopStatusRequest
from repository.shop import suspend_shop, delete_shop, reactivate_shop
from middleware.auth import super_admin_protected_route

router = APIRouter(prefix="/api/v1/shops", tags=["shop"])


@router.post("/{shop_name}/suspend")
async def suspend(shop_name: str, payload: ShopStatusRequest, super_admin=Depends(super_admin_protected_route)): # noqa
    """Super admin only — suspend a shop; every stakeholder there is blocked from logging in""" # noqa
    return await suspend_shop(shop_name, payload.reason, super_admin)


@router.post("/{shop_name}/delete")
async def delete(shop_name: str, payload: ShopStatusRequest, super_admin=Depends(super_admin_protected_route)): # noqa
    """Super admin only — soft delete a shop; data is kept, login is blocked""" # noqa
    return await delete_shop(shop_name, payload.reason, super_admin)


@router.post("/{shop_name}/reactivate")
async def reactivate(shop_name: str, super_admin=Depends(super_admin_protected_route)): # noqa
    """Super admin only — restore a suspended or deleted shop"""
    return await reactivate_shop(shop_name, super_admin)
