from fastapi import APIRouter, Depends, BackgroundTasks, Query
from schema.broadcast import BroadcastSmsRequest
from repository.broadcast import (
    send_shop_broadcast,
    count_broadcast_recipients,
    count_shop_admin_recipients,
    send_shop_admin_broadcast,
)
from middleware.auth import admin_protected_route, super_admin_protected_route, get_current_user, require_permission, require_any_permission

router = APIRouter(prefix="/api/v1/broadcast", tags=["broadcast"])


@router.get("/recipients-count")
async def get_recipients_count(
    branch_name: str | None = Query(default=None, description="Optional branch filter"),
    worker_id: str = Depends(require_any_permission("can_sms_own_branch", "can_sms_all_branches")),
):
    """Permission: can_sms_own_branch or can_sms_all_branches — how many customers a broadcast would reach"""
    return await count_broadcast_recipients(worker_id, branch_name)


@router.post("/sms")
async def broadcast_sms(
    payload: BroadcastSmsRequest,
    background_tasks: BackgroundTasks,
    worker_id: str = Depends(require_any_permission("can_sms_own_branch", "can_sms_all_branches")),
):
    """Permission: can_sms_own_branch or can_sms_all_branches — send SMS"""
    return await send_shop_broadcast(payload.message, worker_id, background_tasks, payload.branch_name)


@router.get("/shop-admins/recipients-count")
async def get_shop_admin_recipients_count(super_admin=Depends(super_admin_protected_route)): # noqa
    """Super admin only — how many shop admins have a phone number on file"""
    return await count_shop_admin_recipients()


@router.post("/shop-admins/sms")
async def broadcast_shop_admins_sms(payload: BroadcastSmsRequest, background_tasks: BackgroundTasks, super_admin=Depends(super_admin_protected_route)): # noqa
    """Super admin only — send a custom SMS to every shop admin across the platform""" # noqa
    return await send_shop_admin_broadcast(payload.message, background_tasks)
