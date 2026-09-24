from fastapi import APIRouter, Depends, BackgroundTasks, Query
from schema.broadcast import BroadcastSmsRequest
from repository.broadcast import (
    send_shop_broadcast,
    count_broadcast_recipients,
    count_shop_admin_recipients,
    send_shop_admin_broadcast,
)
from middleware.auth import admin_protected_route, super_admin_protected_route, get_current_user

router = APIRouter(prefix="/api/v1/broadcast", tags=["broadcast"])


@router.get("/recipients-count")
async def get_recipients_count(
    branch_name: str | None = Query(default=None, description="Optional branch filter"),
    user=Depends(get_current_user),
):
    """How many customers a broadcast would reach right now (optionally filtered by branch)"""
    user_id = str(user.get("sub"))
    return await count_broadcast_recipients(user_id, branch_name)


@router.post("/sms")
async def broadcast_sms(
    payload: BroadcastSmsRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    """Send SMS to customers (optionally targeted by branch)"""
    user_id = str(user.get("sub"))
    return await send_shop_broadcast(payload.message, user_id, background_tasks, payload.branch_name)


@router.get("/shop-admins/recipients-count")
async def get_shop_admin_recipients_count(super_admin=Depends(super_admin_protected_route)): # noqa
    """Super admin only — how many shop admins have a phone number on file"""
    return await count_shop_admin_recipients()


@router.post("/shop-admins/sms")
async def broadcast_shop_admins_sms(payload: BroadcastSmsRequest, background_tasks: BackgroundTasks, super_admin=Depends(super_admin_protected_route)): # noqa
    """Super admin only — send a custom SMS to every shop admin across the platform""" # noqa
    return await send_shop_admin_broadcast(payload.message, background_tasks)
