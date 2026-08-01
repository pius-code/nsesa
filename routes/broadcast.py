from fastapi import APIRouter, Depends, BackgroundTasks
from schema.broadcast import BroadcastSmsRequest
from repository.broadcast import (
    send_shop_broadcast,
    count_broadcast_recipients,
    count_shop_admin_recipients,
    send_shop_admin_broadcast,
)
from middleware.auth import admin_protected_route, super_admin_protected_route

router = APIRouter(prefix="/api/v1/broadcast", tags=["broadcast"])


@router.get("/recipients-count")
async def get_recipients_count(admin=Depends(admin_protected_route)): # noqa
    """Admin only — how many customers a broadcast would reach right now"""
    return await count_broadcast_recipients(admin)


@router.post("/sms")
async def broadcast_sms(payload: BroadcastSmsRequest, background_tasks: BackgroundTasks, admin=Depends(admin_protected_route)): # noqa
    """Admin only — send a custom SMS to every customer who's ever bought from this shop""" # noqa
    return await send_shop_broadcast(payload.message, admin, background_tasks)


@router.get("/shop-admins/recipients-count")
async def get_shop_admin_recipients_count(super_admin=Depends(super_admin_protected_route)): # noqa
    """Super admin only — how many shop admins have a phone number on file"""
    return await count_shop_admin_recipients()


@router.post("/shop-admins/sms")
async def broadcast_shop_admins_sms(payload: BroadcastSmsRequest, background_tasks: BackgroundTasks, super_admin=Depends(super_admin_protected_route)): # noqa
    """Super admin only — send a custom SMS to every shop admin across the platform""" # noqa
    return await send_shop_admin_broadcast(payload.message, background_tasks)
