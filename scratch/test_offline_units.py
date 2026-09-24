import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_schemas():
    from schema.branch import BranchCreate, BranchUpdate, BranchResponse
    from schema.inventory import InventoryCreate, InventoryUpdate
    from schema.stakeholder import adminStakeholderCreateWorker
    from schema.transaction import TransactionCreate, TransactionItemCreate

    # 1. BranchCreate
    bc = BranchCreate(
        branch_name="Osu Branch",
        location="Oxford St, Accra",
        phone="0244123456",
        is_main=True,
    )
    assert bc.branch_name == "Osu Branch"
    assert bc.is_main is True
    print("[PASS] BranchCreate schema validated")

    # 2. BranchUpdate
    bu = BranchUpdate(location="East Legon", is_active=False)
    assert bu.location == "East Legon"
    assert bu.is_active is False
    print("[PASS] BranchUpdate schema validated")

    # 3. BranchResponse
    br = BranchResponse(
        id="64f1234567890abcdef12345",
        shop_name="Test Shop",
        branch_name="Osu Branch",
        location="Oxford St, Accra",
        phone="0244123456",
        is_main=True,
        is_active=True,
        worker_count=4,
        inventory_count=42,
    )
    assert br.worker_count == 4
    assert br.inventory_count == 42
    print("[PASS] BranchResponse schema validated")

    # 4. InventoryCreate with branch_name
    ic = InventoryCreate(
        product_name="Milo 400g",
        product_price=25.0,
        amount_available=100,
        branch_name="Osu Branch",
    )
    assert ic.branch_name == "Osu Branch"
    print("[PASS] InventoryCreate with branch_name validated")

    # 5. Worker creation with worker_branch_name
    wc = adminStakeholderCreateWorker(
        worker_name="Kwame",
        worker_email="kwame@osu.com",
        worker_password="password123",
        worker_role="worker",
        worker_branch_name="Osu Branch",
    )
    assert wc.worker_branch_name == "Osu Branch"
    print("[PASS] adminStakeholderCreateWorker with worker_branch_name validated")

    # 6. TransactionCreate with branch_name
    tc = TransactionCreate(
        customer_name="Ama",
        customer_number="0244987654",
        payment_mode="cash",
        processed_by="Kwame",
        total_price=50.0,
        items=[
            TransactionItemCreate(
                product_id="64f1234567890abcdef12345",
                product_name="Milo 400g",
                unit_price=25.0,
                quantity=2,
                subtotal=50.0,
            )
        ],
        branch_name="Osu Branch",
    )
    assert tc.branch_name == "Osu Branch"
    print("[PASS] TransactionCreate with branch_name validated")

def test_models():
    from model.Branch import Branch
    from model.Shop import Shop
    from model.Inventory import Inventory
    from model.Transaction import Transaction

    # Check Branch fields
    assert "shop_name" in Branch.model_fields
    assert "branch_name" in Branch.model_fields
    assert "is_main" in Branch.model_fields
    print("[PASS] Branch model structure validated")

    # Check Shop sms_sent_count
    assert "sms_sent_count" in Shop.model_fields
    assert Shop.model_fields["sms_sent_count"].default == 0
    print("[PASS] Shop.sms_sent_count field validated")

    # Check Inventory branch_name
    assert "branch_name" in Inventory.model_fields
    print("[PASS] Inventory.branch_name field validated")

    # Check Transaction branch_name
    assert "branch_name" in Transaction.model_fields
    print("[PASS] Transaction.branch_name field validated")

def test_fastapi_routes():
    from main import app

    routes = {route.path: route for route in app.routes}

    # Verify Branch routes exist
    assert "/api/v1/branches" in routes, "Missing /api/v1/branches route"
    assert "/api/v1/branches/{branch_id}" in routes, "Missing /api/v1/branches/{branch_id} route"

    # Verify Admin shop details route exists
    assert "/api/v1/admin/shops/{shop_name}/details" in routes, "Missing /api/v1/admin/shops/{shop_name}/details route"

    # Verify inventory route accepts branch_name
    inv_route = routes.get("/api/v1/inventory/get_my_shop_inventory")
    assert inv_route is not None, "Missing /api/v1/inventory/get_my_shop_inventory"
    param_names = [p.name for p in inv_route.dependant.query_params]
    assert "branch_name" in param_names, f"Expected 'branch_name' in query params, got {param_names}"

    # Verify transaction route accepts branch_name
    tx_route = routes.get("/api/v1/return_my_shop_transactions")
    assert tx_route is not None, "Missing /api/v1/return_my_shop_transactions"
    tx_param_names = [p.name for p in tx_route.dependant.query_params]
    assert "branch_name" in tx_param_names, f"Expected 'branch_name' in query params, got {tx_param_names}"

    print("[PASS] All FastAPI route definitions and query parameters validated")

if __name__ == "__main__":
    test_schemas()
    test_models()
    test_fastapi_routes()
    print("\nALL OFFLINE TESTS PASSED! 100% OK!")
