import asyncio
from types import SimpleNamespace

from repository import transaction as tx_repo
from repository.payment import PaymentService
from schema.payment import PaymentReconcileRequest


def test_save_an_nsesa_transaction_links_payment_and_receipt(monkeypatch):
    inventory = SimpleNamespace(
        id="67ab9fd8b76f4a3b0c3ab3d2",
        product_name="Rice 25kg",
        product_price=90.0,
        cost_price=60.0,
        amount_available=5,
        sku="RICE-25",
        barcode=None,
        is_available=True,
    )

    async def _fake_inc(changes):
        for key, value in changes.items():
            if key == "amount_available":
                inventory.amount_available += value

    async def _fake_set(changes):
        for key, value in changes.items():
            setattr(inventory, key, value)

    async def _fake_inventory_get(_id):
        return inventory

    async def _fake_stock_movement_record(**kwargs):
        return SimpleNamespace(id="mov-1")

    async def _fake_stakeholder_find_one(**kwargs):
        return SimpleNamespace(worker_shop_image="https://example.com/shop.png")

    async def _fake_client_get(_id):
        return None

    class FakeTransaction:
        def __init__(self, **kwargs):
            self.branch_name = "Main Branch"
            for key, value in kwargs.items():
                setattr(self, key, value)

        async def insert(self):
            return None

        async def save(self):
            return None

    captured = {}

    async def _fake_initiate_payment(payload, shop_name, user_id, user_name):
        captured["payload"] = payload
        captured["shop_name"] = shop_name
        return SimpleNamespace(
            id="pay-123",
            payment_reference="FJPAY-ABC123",
            payment_mode=payload.payment_mode.upper(),
        )

    monkeypatch.setattr(inventory, "inc", _fake_inc, raising=False)
    monkeypatch.setattr(inventory, "set", _fake_set, raising=False)
    monkeypatch.setattr(tx_repo.Inventory, "get", _fake_inventory_get)
    monkeypatch.setattr(tx_repo.StockMovementService, "record_movement", _fake_stock_movement_record)
    monkeypatch.setattr(tx_repo.Stakeholder, "find_one", _fake_stakeholder_find_one)
    monkeypatch.setattr(tx_repo.Client, "get", _fake_client_get)
    monkeypatch.setattr(tx_repo, "Transaction", FakeTransaction)
    monkeypatch.setattr(tx_repo, "PaymentService", SimpleNamespace(initiate_payment=_fake_initiate_payment))

    payload = tx_repo.TransactionCreate(
        items=[
            tx_repo.TransactionItemCreate(
                product_id="67ab9fd8b76f4a3b0c3ab3d2",
                product_name="Rice 25kg",
                unit_price=90.0,
                quantity=2,
                subtotal=180.0,
            )
        ],
        total_price=180.0,
        processed_by="Jane",
        processed_by_id="worker-1",
        customer_name="Ada",
        payment_mode="CASH",
        send_sms=False,
    )

    result = asyncio.run(tx_repo.save_an_nsesa_transaction(payload, shop_name="Nimble Mart"))

    assert result["message"] == "Transaction saved successfully"
    assert captured["payload"].transaction_id == result["transaction_id"]
    assert captured["payload"].amount == 180.0
    assert captured["payload"].payment_mode == "CASH"
    assert captured["shop_name"] == "Nimble Mart"


def test_complete_pending_payment_creates_payment_reference_and_receipt_metadata(monkeypatch):
    captured = {}

    class FakePaymentService:
        @staticmethod
        async def initiate_payment(payload, shop_name, user_id, user_name):
            captured["payload"] = payload
            captured["shop_name"] = shop_name
            captured["user_id"] = user_id
            captured["user_name"] = user_name
            return SimpleNamespace(id="pay-queued", payment_reference="FJPAY-PEND1", payment_mode="CARD")

    class FakeTransaction:
        def __init__(self, **kwargs):
            self.id = "tx-pending-1"
            self.branch_name = "Main Branch"
            self.customer_number = "0244000000"
            self.customer_name = "Ada"
            self.customer_email = "ada@example.com"
            self.receipt_id = "nimble-ABC123"
            self.total_price = 180.0
            self.items = []
            self.status = "pending"
            self.payment_mode = None
            self.payment_id = None
            self.payment_reference = None
            for key, value in kwargs.items():
                setattr(self, key, value)

        async def save(self):
            captured["saved"] = True
            return None

    txn = FakeTransaction()

    async def _fake_get_admin_and_shop(worker_id):
        return SimpleNamespace(worker_shop_name="Nimble Mart", worker_name="Jane", id=worker_id)

    async def _fake_get_transaction_in_shop(transaction_id, shop_name):
        assert transaction_id == "tx-pending-1"
        assert shop_name == "Nimble Mart"
        return txn

    async def _fake_log_transaction_action(**kwargs):
        captured["audit"] = kwargs

    monkeypatch.setattr(tx_repo, "PaymentService", FakePaymentService)
    monkeypatch.setattr(tx_repo, "_get_admin_and_shop", _fake_get_admin_and_shop)
    monkeypatch.setattr(tx_repo, "_get_transaction_in_shop", _fake_get_transaction_in_shop)
    monkeypatch.setattr(tx_repo, "log_transaction_action", _fake_log_transaction_action)

    result = asyncio.run(
        tx_repo.complete_pending_payment(
            "tx-pending-1",
            tx_repo.CompletePaymentRequest(payment_mode="card", send_sms=False),
            "worker-1",
            None,
        )
    )

    assert result["message"] == "Payment recorded successfully"
    assert txn.status == "success"
    assert txn.payment_mode == "CARD"
    assert txn.payment_id == "pay-queued"
    assert txn.payment_reference == "FJPAY-PEND1"
    assert captured["shop_name"] == "Nimble Mart"
    assert captured["payload"].transaction_id == "tx-pending-1"
    assert captured["payload"].receipt_id == "nimble-ABC123"
    assert captured["payload"].amount == 180.0


def test_reconcile_payment_updates_the_linked_transaction(monkeypatch):
    class FakePayment:
        def __init__(self):
            self.id = "pay-abc"
            self.payment_reference = "FJPAY-REC1"
            self.transaction_id = "tx-123"
            self.receipt_id = "nimble-REC1"
            self.amount = 120.0
            self.shop_name = "Nimble Mart"
            self.payment_mode = "BANK_TRANSFER"
            self.status = "PENDING"
            self.metadata = {}
            self.failure_reason = None

        async def save(self):
            return None

    class FakeTransaction:
        def __init__(self):
            self.id = "tx-123"
            self.status = "pending"
            self.payment_id = None
            self.payment_reference = None
            self.payment_mode = None
            self.receipt_id = "nimble-REC1"
            self.at_shop = "Nimble Mart"

        async def save(self):
            return None

    payment = FakePayment()
    transaction = FakeTransaction()

    async def _fake_find_one(*args, **kwargs):
        return payment

    async def _fake_transaction_get(_id):
        return transaction

    monkeypatch.setattr("repository.payment.Payment.find_one", _fake_find_one)
    monkeypatch.setattr("repository.payment.Transaction.get", _fake_transaction_get)

    result = asyncio.run(
        PaymentService.reconcile_payment(
            PaymentReconcileRequest(
                payment_reference="FJPAY-REC1",
                action="APPROVE",
                reason="Bank proof received",
            ),
            shop_name="Nimble Mart",
            user_name="Jane",
        )
    )

    assert result.status == "SUCCESS"
    assert transaction.status == "success"
    assert transaction.payment_reference == "FJPAY-REC1"
    assert transaction.payment_mode == "BANK_TRANSFER"
    assert transaction.payment_id == "pay-abc"


def test_public_receipt_payload_hides_sensitive_fields(monkeypatch):
    item = SimpleNamespace(
        product_name="Rice 25kg",
        quantity=2,
        unit_price=90.0,
        subtotal=180.0,
        discount=0.0,
        tax_rate=0.0,
        refunded_quantity=0,
    )
    transaction = SimpleNamespace(
        receipt_id="nimble-ABC123",
        customer_name="Ada",
        customer_number="0244000000",
        customer_email="ada@example.com",
        total_price=180.0,
        payment_mode="CASH",
        status="success",
        items=[item],
        at_shop="Nimble Mart",
        shop_image="https://example.com/logo.png",
        created_at="2026-09-14T12:00:00Z",
        payment_reference="FJPAY-ABC123",
        payment_id="pay-123",
        processed_by_id="worker-1",
        note="No pepper",
    )

    async def _fake_find_one(*args, **kwargs):
        return transaction

    async def _fake_stakeholder_find_one(**kwargs):
        return SimpleNamespace(worker_shop_image="https://example.com/logo.png")

    monkeypatch.setattr(tx_repo.Transaction, "find_one", _fake_find_one)
    monkeypatch.setattr(tx_repo.Stakeholder, "find_one", _fake_stakeholder_find_one)

    result = asyncio.run(tx_repo.get_public_receipt_payload("nimble-ABC123"))

    assert result["receipt_id"] == "nimble-ABC123"
    assert result["customer_name"] == "Ada"
    assert result["total_price"] == 180.0
    assert result["items"][0]["product_name"] == "Rice 25kg"
    assert "customer_number" not in result
    assert "customer_email" not in result
    assert "payment_id" not in result
    assert "processed_by_id" not in result


def test_dashboard_overview_returns_summary_values(monkeypatch):
    class FakeQueryField:
        def __init__(self, value=None):
            self.value = value

        def __eq__(self, other):
            return True

        def __ge__(self, other):
            return True

        def __lt__(self, other):
            return True

    class FakeInventoryFind:
        def __init__(self, rows):
            self.rows = rows

        def sort(self, *_args, **_kwargs):
            return self

        async def to_list(self):
            return self.rows

    async def _fake_run_aggregation(pipeline):
        match_stage = next((step["$match"] for step in pipeline if isinstance(step, dict) and "$match" in step), {})
        group_stage = next((step["$group"] for step in pipeline if isinstance(step, dict) and "$group" in step), {})
        count_stage = next((step["$count"] for step in pipeline if isinstance(step, dict) and "$count" in step), None)

        if match_stage.get("status") == "pending":
            return [{"count": 2, "value": 60.0}]
        if count_stage == "count":
            return [{"count": 12}]
        if group_stage.get("_id") == "$payment_mode":
            return [{"payment_mode": "CASH", "total": 300.0, "count": 2}]
        if group_stage.get("_id") == "$items.product_id":
            return [{"_id": "prod-1", "product_name": "Rice", "quantity_sold": 10, "revenue": 250.0}]
        if match_stage.get("status") == "success" and "created_at" in match_stage:
            return [{"revenue": 500.0, "count": 4}]
        return []

    class FakeTransactionAuditFind:
        def __init__(self, rows):
            self.rows = rows

        async def to_list(self):
            return self.rows

    class FakeTransactionFind:
        def __init__(self, rows):
            self.rows = rows

        async def to_list(self):
            return self.rows

    async def _fake_get_distinct(_field, _filter):
        return ["Ada", "Sam", "customer"]

    monkeypatch.setattr("repository.dashboard._run_aggregation", _fake_run_aggregation)
    monkeypatch.setattr("repository.dashboard.Inventory.worker_shop_name", FakeQueryField("Nimble Mart"), raising=False)
    monkeypatch.setattr("repository.dashboard.Inventory.is_deleted", FakeQueryField(False), raising=False)
    monkeypatch.setattr("repository.dashboard.Inventory.amount_available", FakeQueryField(2), raising=False)
    monkeypatch.setattr("repository.dashboard.Inventory.find", lambda *args, **kwargs: FakeInventoryFind([SimpleNamespace(id="inv-1", product_name="Rice", amount_available=2)]))
    monkeypatch.setattr("repository.dashboard.TransactionAudit.action", FakeQueryField("refunded"), raising=False)
    monkeypatch.setattr("repository.dashboard.TransactionAudit.at_shop", FakeQueryField("Nimble Mart"), raising=False)
    monkeypatch.setattr("repository.dashboard.TransactionAudit.created_at", FakeQueryField(), raising=False)
    monkeypatch.setattr("repository.dashboard.TransactionAudit.find", lambda *args, **kwargs: FakeTransactionAuditFind([SimpleNamespace(transaction_id="507f1f77bcf86cd799439011")]))
    monkeypatch.setattr("repository.dashboard.Transaction.id", "id", raising=False)
    monkeypatch.setattr("repository.dashboard.Transaction.find", lambda *args, **kwargs: FakeTransactionFind([SimpleNamespace(total_price=30.0)]))
    monkeypatch.setattr("repository.dashboard.Transaction.get_pymongo_collection", lambda: SimpleNamespace(distinct=_fake_get_distinct))

    result = asyncio.run(tx_repo.get_dashboard_overview("Nimble Mart"))

    assert result.today_revenue == 500.0
    assert result.today_transaction_count == 4
    assert result.payment_breakdown_today[0].payment_mode == "CASH"
    assert result.top_products_week[0].product_name == "Rice"
    assert result.low_stock_items[0].product_name == "Rice"
    assert result.pending_order_count == 2
    assert result.month_completed_transaction_count == 12
