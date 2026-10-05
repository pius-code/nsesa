from fastapi import APIRouter, Depends, BackgroundTasks
from schema.stakeholder import ForgotPasswordRequest, ChangePasswordRequest, AdminResetPasswordRequest
from repository.password import (
    request_password_reset,
    get_pending_password_resets,
    admin_reset_worker_password,
    self_change_password,
)
from middleware.auth import (
    get_current_user,
    admin_protected_route,
    super_admin_protected_route,
    require_any_permission,
)

router = APIRouter(prefix="/api/v1", tags=["password"])


@router.post("/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    """Public endpoint — Submit a request to store admins to reset a forgotten password"""
    return await request_password_reset(payload, background_tasks)


@router.post("/auth/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    """Authenticated self-service — Change own password using current password"""
    return await self_change_password(user.get("sub"), payload, background_tasks)


@router.get("/admin/password-resets")
async def list_pending_resets(
    admin_id: str = Depends(require_any_permission("can_add_others")),
):
    """Admin / Manager — List pending password reset requests for the shop"""
    return await get_pending_password_resets(admin_id)


@router.post("/admin/workers/{worker_id}/reset-password")
async def reset_worker_password(
    worker_id: str,
    payload: AdminResetPasswordRequest,
    background_tasks: BackgroundTasks,
    admin_id: str = Depends(require_any_permission("can_add_others")),
):
    """Admin / Manager — Reset a worker's password with audit logging and optional SMS"""
    return await admin_reset_worker_password(worker_id, payload, admin_id, background_tasks)


@router.post("/super-admin/workers/{worker_id}/reset-password")
async def super_admin_reset(
    worker_id: str,
    payload: AdminResetPasswordRequest,
    background_tasks: BackgroundTasks,
    super_admin_id: str = Depends(super_admin_protected_route),
):
    """Super Admin only — Reset any user or admin's password across the platform"""
    return await admin_reset_worker_password(worker_id, payload, super_admin_id, background_tasks)
