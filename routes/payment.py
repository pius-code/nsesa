from fastapi import APIRouter, Depends, Header
from typing import Optional
from model.Stakeholder import Stakeholder
from middleware.auth import get_current_stakeholder, require_roles
from schema.payment import PaymentInitiateRequest, PaymentVerifyRequest, PaymentReconcileRequest
from repository.payment import PaymentService

payment_router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@payment_router.post("/initiate")
async def initiate_payment(
    payload: PaymentInitiateRequest,
    x_idempotency_key: Optional[str] = Header(None),
    current_user: Stakeholder = Depends(get_current_stakeholder)
):
    if x_idempotency_key and not payload.idempotency_key:
        payload.idempotency_key = x_idempotency_key

    return await PaymentService.initiate_payment(
        payload=payload,
        shop_name=current_user.worker_shop_name,
        user_id=str(current_user.id),
        user_name=current_user.worker_name
    )


@payment_router.get("/verify/{reference}")
async def verify_payment(
    reference: str,
    current_user: Stakeholder = Depends(get_current_stakeholder)
):
    return await PaymentService.verify_payment(reference, current_user.worker_shop_name)


@payment_router.post("/reconcile")
async def reconcile_payment(
    payload: PaymentReconcileRequest,
    current_user: Stakeholder = Depends(require_roles(["owner", "admin", "manager", "accountant"]))
):
    return await PaymentService.reconcile_payment(
        payload=payload,
        shop_name=current_user.worker_shop_name,
        user_name=current_user.worker_name
    )


@payment_router.get("")
async def list_payments(
    limit: int = 50,
    skip: int = 0,
    current_user: Stakeholder = Depends(get_current_stakeholder)
):
    return await PaymentService.get_shop_payments(current_user.worker_shop_name, limit, skip)
