import asyncio
from types import SimpleNamespace

from repository import transaction as tx_repo


def test_save_an_nsesa_transaction_reduces_stock_and_logs_movement(monkeypatch):
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
        _apply_inc(inventory, changes)

    async def _fake_set(changes):
        _apply_set(inventory, changes)

    async def _fake_inventory_get(_id):
        return inventory

    async def _fake_stock_movement_record(**kwargs):
        calls["movement"] = kwargs
        return SimpleNamespace(id="mov-1")

    async def _fake_stakeholder_find_one(**kwargs):
        return SimpleNamespace(worker_shop_image="https://example.com/shop.png")

    class FakeTransaction:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        async def insert(self):
            calls["transaction_inserted"] = True
            return None

    async def _fake_client_get(_id):
        return None

    calls = {
        "movement": None,
        "transaction_inserted": False,
    }

    def _apply_inc(obj, changes):
        for key, value in changes.items():
            if key == "amount_available":
                obj.amount_available += value
        return None

    def _apply_set(obj, changes):
        for key, value in changes.items():
            setattr(obj, key, value)
        return None

    monkeypatch.setattr(inventory, "inc", _fake_inc, raising=False)
    monkeypatch.setattr(inventory, "set", _fake_set, raising=False)
    monkeypatch.setattr(tx_repo.Inventory, "get", _fake_inventory_get)
    monkeypatch.setattr(tx_repo.StockMovementService, "record_movement", _fake_stock_movement_record)
    monkeypatch.setattr(tx_repo.Stakeholder, "find_one", _fake_stakeholder_find_one)
    monkeypatch.setattr(tx_repo.Client, "get", _fake_client_get)
    monkeypatch.setattr(tx_repo, "Transaction", FakeTransaction)

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
    assert inventory.amount_available == 3
    assert inventory.is_available is True
    assert calls["transaction_inserted"] is True
    assert calls["movement"]["movement_type"] == "SALE"
    assert calls["movement"]["quantity_change"] == -2
    assert calls["movement"]["new_quantity"] == 3
