import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from beanie import PydanticObjectId
from model.Payment import Payment
from model.Transaction import Transaction
from schema.payment import PaymentInitiateRequest, PaymentReconcileRequest
from utils.logger import logger
from utils.paystack import paystack_client
from utils.hubtel_sms import send_sms_via_hubtel


class PaymentService:
    @staticmethod
    async def initiate_payment(payload: PaymentInitiateRequest, shop_name: str, user_id: str, user_name: str) -> Payment:
        # 1. Check idempotency key to prevent double charging
        if payload.idempotency_key:
            existing = await Payment.find_one({"idempotency_key": payload.idempotency_key})
            if existing:
                return existing

        # 2. Generate unique payment reference
        ref = f"FJPAY-{uuid.uuid4().hex[:10].upper()}"
        mode = payload.payment_mode.upper()
        provider = payload.payment_provider or mode

        status = "PENDING"
        provider_ref = None
        metadata = payload.metadata or {}

        # 3. Provider-specific handling
        if mode == "CASH":
            status = "SUCCESS"
            provider = "CASH"
        elif mode == "PAY_LATER":
            status = "SUCCESS"
            provider = "INTERNAL_LEDGER"
        elif mode == "BANK_TRANSFER":
            status = "PENDING"  # Merchant must confirm receipt or reconcile
            provider = "BANK"
        elif mode == "QR":
            status = "PENDING"
            provider = "QR_GHANA"
        elif mode in ("MOMO", "CARD"):
            # If Paystack / Hubtel keys configured, integrate
            if paystack_client and payload.customer_email:
                try:
                    init_res = paystack_client.initialize_transaction(
                        email=payload.customer_email,
                        amount=payload.amount,
                        reference=ref,
                        metadata={"shop_name": shop_name, "mode": mode}
                    )
                    provider_ref = init_res.get("data", {}).get("reference")
                    metadata["authorization_url"] = init_res.get("data", {}).get("authorization_url")
                except Exception as e:
                    logger.error(f"Paystack payment initialization failed: {e}")
                    # Keep pending for direct merchant mobile prompt fallback
            status = "PENDING"

        payment = Payment(
            payment_reference=ref,
            idempotency_key=payload.idempotency_key,
            transaction_id=payload.transaction_id,
            receipt_id=payload.receipt_id,
            shop_name=shop_name,
            branch_name=payload.branch_name or "Main Branch",
            amount=payload.amount,
            currency="GHS",
            payment_mode=mode,
            payment_provider=provider,
            provider_reference=provider_ref,
            status=status,
            customer_name=payload.customer_name,
            customer_phone=payload.customer_phone,
            customer_email=payload.customer_email,
            processed_by_id=user_id,
            processed_by_name=user_name,
            metadata=metadata,
        )
        await payment.insert()

        # Update transaction if linked
        if payload.transaction_id:
            try:
                tx = await Transaction.get(PydanticObjectId(payload.transaction_id))
                if tx and tx.at_shop == shop_name:
                    tx.payment_id = str(payment.id)
                    tx.payment_reference = ref
                    tx.payment_mode = mode
                    await tx.save()
            except Exception as e:
                logger.warning(f"Failed to link payment {ref} to transaction: {e}")

        return payment

    @staticmethod
    async def verify_payment(reference: str, shop_name: str) -> Payment:
        payment = await Payment.find_one({
            "payment_reference": reference,
            "shop_name": shop_name,
        })
        if not payment:
            raise HTTPException(status_code=404, detail="Payment reference not found")

        # If payment is external (Paystack)
        if payment.payment_provider == "PAYSTACK" and payment.status == "PENDING":
            try:
                verify_res = paystack_client.verify_transaction(reference)
                if verify_res.get("data", {}).get("status") == "success":
                    payment.status = "SUCCESS"
                    await payment.save()
            except Exception as e:
                logger.error(f"Error verifying payment with Paystack: {e}")

        return payment

    @staticmethod
    async def reconcile_payment(payload: PaymentReconcileRequest, shop_name: str, user_name: str) -> Payment:
        payment = await Payment.find_one({
            "payment_reference": payload.payment_reference,
            "shop_name": shop_name,
        })
        if not payment:
            raise HTTPException(status_code=404, detail="Payment reference not found")

        if payload.action == "APPROVE":
            payment.status = "SUCCESS"
        elif payload.action == "REJECT":
            payment.status = "FAILED"
            payment.failure_reason = payload.reason
        elif payload.action == "REFUND":
            payment.status = "REFUNDED"

        payment.metadata = payment.metadata or {}
        payment.metadata["reconciled_by"] = user_name
        payment.metadata["reconciliation_reason"] = payload.reason
        payment.metadata["reconciled_at"] = datetime.now(timezone.utc).isoformat()
        await payment.save()

        if payment.transaction_id:
            try:
                try:
                    transaction = await Transaction.get(PydanticObjectId(payment.transaction_id))
                except Exception:
                    transaction = await Transaction.get(payment.transaction_id)

                if transaction and transaction.at_shop == shop_name:
                    transaction.payment_id = str(payment.id)
                    transaction.payment_reference = payment.payment_reference
                    transaction.payment_mode = payment.payment_mode
                    if getattr(transaction, "status", None) in {"pending", "PENDING", None}:
                        transaction.status = "success"
                    await transaction.save()
            except Exception:
                pass

        return payment

    @staticmethod
    async def get_shop_payments(shop_name: str, limit: int = 50, skip: int = 0) -> list[Payment]:
        return await Payment.find({"shop_name": shop_name}).sort(-Payment.created_at).skip(skip).limit(limit).to_list()
