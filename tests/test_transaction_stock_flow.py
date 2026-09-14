import asyncio
from types import SimpleNamespace

from repository import transaction as tx_repo


def test_cancel_pending_order_restocks_and_marks_deleted(monkeypatch):
    calls = {}

    async def fake_get_admin_and_shop(_id):
        return SimpleNamespace(worker_shop_name="Nimble Mart", worker_name="Jane")

    async def fake_restock(items, shop_name, user_id, user_name, movement_type="REFUND", reason="Transaction Refund / Restock"):
        calls["items"] = items
        calls["shop_name"] = shop_name
        calls["user_id"] = user_id
        calls["user_name"] = user_name
        calls["movement_type"] = movement_type
        calls["reason"] = reason

    async def fake_log_transaction_action(**kwargs):
        return None

    async def fake_save():
        return None

    txn = SimpleNamespace(
        id="txn-123",
        items=[SimpleNamespace(product_id="p1", quantity=2, unit_price=3.5)],
        status="pending",
        is_deleted=False,
        customer_name="Ada",
    )
    txn.save = fake_save

    async def fake_get_transaction_in_shop(_id, shop_name):
        return txn

    monkeypatch.setattr(tx_repo, "_get_admin_and_shop", fake_get_admin_and_shop)
    monkeypatch.setattr(tx_repo, "_get_transaction_in_shop", fake_get_transaction_in_shop)
    monkeypatch.setattr(tx_repo, "_restock_items", fake_restock)
    monkeypatch.setattr(tx_repo, "log_transaction_action", fake_log_transaction_action)

    result = asyncio.run(
        tx_repo.cancel_pending_order("txn-123", SimpleNamespace(reason="customer cancelled"), "worker-1")
    )

    assert result["message"] == "Order cancelled successfully"
    assert txn.is_deleted is True
    assert calls["shop_name"] == "Nimble Mart"
    assert calls["user_id"] == "worker-1"
    assert calls["user_name"] == "Jane"
    assert calls["movement_type"] == "RESTOCK"
    assert "customer cancelled" in calls["reason"]
