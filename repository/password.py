from fastapi import HTTPException, BackgroundTasks
from beanie import PydanticObjectId
from datetime import datetime, timezone
from model.Stakeholder import Stakeholder
from model.PasswordResetRequest import PasswordResetRequest
from model.PasswordResetAuditLog import PasswordResetAuditLog
from schema.stakeholder import ForgotPasswordRequest, ChangePasswordRequest, AdminResetPasswordRequest
from utils.hasher import hashPwd, verifyPwd
from utils.arkesel_sms import send_worker_sms


async def request_password_reset(payload: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    email = payload.email.strip().lower()
    # Case-insensitive search
    stakeholder = await Stakeholder.find_one(Stakeholder.worker_email == email)
    if not stakeholder:
        # Standard security practice: generic message to prevent email enumeration
        return {
            "message": "If an account matches that email, your store administrator has been notified."
        }

    # Check for existing active pending request to avoid duplicates
    existing = await PasswordResetRequest.find_one(
        PasswordResetRequest.worker_id == str(stakeholder.id),
        PasswordResetRequest.status == "pending",
    )
    if not existing:
        reset_req = PasswordResetRequest(
            worker_id=str(stakeholder.id),
            worker_name=stakeholder.worker_name,
            worker_email=stakeholder.worker_email,
            worker_phone=stakeholder.worker_phone,
            worker_branch_name=stakeholder.worker_branch_name,
            shop_name=stakeholder.worker_shop_name,
            status="pending",
        )
        await reset_req.insert()

    # Send confirmation SMS to worker if phone number exists
    if stakeholder.worker_phone:
        msg = (
            f"Hello {stakeholder.worker_name}, your password reset request for "
            f"'{stakeholder.worker_shop_name}' was received. Please contact your manager to get your new password."
        )
        background_tasks.add_task(
            send_worker_sms,
            stakeholder.worker_phone,
            msg,
            stakeholder.worker_shop_name,
        )

    return {
        "message": "Your administrators have been notified. Please follow up with them to reset your password."
    }


async def get_pending_password_resets(admin_id: str):
    admin = await Stakeholder.get(PydanticObjectId(admin_id))
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    shop_name = admin.worker_shop_name
    query = {"status": "pending"}
    if admin.worker_role != "super_admin":
        query["shop_name"] = shop_name

    requests = await PasswordResetRequest.find(query).sort("-requested_at").to_list()

    return {
        "count": len(requests),
        "requests": [
            {
                "id": str(r.id),
                "worker_id": r.worker_id,
                "worker_name": r.worker_name,
                "worker_email": r.worker_email,
                "worker_phone": r.worker_phone,
                "worker_branch_name": r.worker_branch_name,
                "shop_name": r.shop_name,
                "requested_at": r.requested_at,
            }
            for r in requests
        ],
    }


async def admin_reset_worker_password(
    target_worker_id: str,
    payload: AdminResetPasswordRequest,
    admin_id: str,
    background_tasks: BackgroundTasks,
):
    admin = await Stakeholder.get(PydanticObjectId(admin_id))
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    worker = await Stakeholder.get(PydanticObjectId(target_worker_id))
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Ensure worker belongs to admin's shop (unless super_admin)
    if admin.worker_role != "super_admin" and worker.worker_shop_name != admin.worker_shop_name:
        raise HTTPException(status_code=403, detail="Cannot reset password for workers outside your shop")

    # Update worker password
    worker.worker_hashed_password = hashPwd(payload.new_password)
    await worker.save()

    # Record immutable audit log
    audit = PasswordResetAuditLog(
        worker_id=str(worker.id),
        worker_name=worker.worker_name,
        changed_by_id=str(admin.id),
        changed_by_name=admin.worker_name,
        changed_by_role=admin.worker_role,
        reason=payload.reason.strip() or "Manager reset",
        shop_name=worker.worker_shop_name,
    )
    await audit.insert()

    # Mark any pending requests as resolved
    pending_requests = await PasswordResetRequest.find(
        PasswordResetRequest.worker_id == str(worker.id),
        PasswordResetRequest.status == "pending",
    ).to_list()
    for req in pending_requests:
        req.status = "resolved"
        req.resolved_at = datetime.now(timezone.utc)
        req.resolved_by = admin.worker_name
        req.resolution_notes = payload.reason
        await req.save()

    # Send SMS notification to the worker
    if payload.send_sms and worker.worker_phone:
        sms_body = (
            f"Hello {worker.worker_name}, your password for '{worker.worker_shop_name}' "
            f"has been reset. If you did not request this change, please contact an administrator."
        )
        background_tasks.add_task(
            send_worker_sms,
            worker.worker_phone,
            sms_body,
            worker.worker_shop_name,
        )

    return {
        "message": f"Password reset successfully for {worker.worker_name}.",
        "worker_id": str(worker.id),
    }


async def self_change_password(
    user_id: str,
    payload: ChangePasswordRequest,
    background_tasks: BackgroundTasks,
):
    worker = await Stakeholder.get(PydanticObjectId(user_id))
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    if not verifyPwd(payload.current_password, worker.worker_hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    worker.worker_hashed_password = hashPwd(payload.new_password)
    await worker.save()

    # Record audit log
    audit = PasswordResetAuditLog(
        worker_id=str(worker.id),
        worker_name=worker.worker_name,
        changed_by_id=str(worker.id),
        changed_by_name=worker.worker_name,
        changed_by_role=worker.worker_role,
        reason="Self-service password update",
        shop_name=worker.worker_shop_name,
    )
    await audit.insert()

    if worker.worker_phone:
        msg = (
            f"Hello {worker.worker_name}, your password for '{worker.worker_shop_name}' "
            f"has been reset. If you did not make this change, please contact an administrator."
        )
        background_tasks.add_task(
            send_worker_sms,
            worker.worker_phone,
            msg,
            worker.worker_shop_name,
        )

    return {"message": "Password changed successfully."}
