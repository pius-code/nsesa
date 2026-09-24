import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

async def run_tests():
    from motor.motor_asyncio import AsyncIOMotorClient
    from beanie import init_beanie
    from model import Nsesa_model
    from model.Branch import Branch
    from model.Shop import Shop
    from model.Inventory import Inventory
    from model.Transaction import Transaction
    from model.Stakeholder import Stakeholder
    from schema.branch import BranchCreate, BranchUpdate
    from repository.branch import create_branch, get_shop_branches, update_branch, delete_branch
    from repository.stakeholder import get_all_shops, get_shop_details_for_super_admin

    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        print("MONGO_URL not found, skipping db connectivity test.")
        return

    client = AsyncIOMotorClient(mongo_url)
    db = client.get_default_database()
    await init_beanie(database=db, document_models=Nsesa_model)
    print("[PASS] Beanie initialized with all models including Branch successfully")

    # 1. Test Branch Schemas
    payload = BranchCreate(
        branch_name="Test Osu Branch",
        location="Oxford St, Accra",
        phone="0244111222",
        is_main=True,
    )
    assert payload.branch_name == "Test Osu Branch"
    print("[PASS] BranchCreate schema validated")

    # 2. Test mock admin user for branch creation
    TEST_SHOP = "test_multibranch_shop"
    # Clean up any leftover test data
    await Branch.find(Branch.shop_name == TEST_SHOP).delete()

    test_admin = Stakeholder(
        worker_name="Test Admin",
        worker_email="testadmin_branch@test.com",
        worker_hashed_password="hashed_password123",
        worker_shop_name=TEST_SHOP,
        worker_role="admin",
        worker_branch_name="Main",
    )
    await test_admin.insert()
    admin_id = str(test_admin.id)
    print("[PASS] Created test admin")

    try:
        # 3. Create Branch via repository
        res = await create_branch(payload, admin_id)
        assert res.id is not None
        branch_id = res.id
        print(f"[PASS] create_branch succeeded: {branch_id}")

        # 4. Fetch branches
        branches = await get_shop_branches(TEST_SHOP)
        assert len(branches) == 1
        assert branches[0].branch_name == "Test Osu Branch"
        assert branches[0].is_main is True
        print("[PASS] get_shop_branches returned created branch with counts")

        # 5. Update Branch
        update_res = await update_branch(branch_id, BranchUpdate(location="New Location, Accra"), admin_id)
        assert update_res.location == "New Location, Accra"
        print("[PASS] update_branch succeeded")

        # 6. Test super admin shop details query
        details = await get_shop_details_for_super_admin(TEST_SHOP)
        assert details["shop_name"] == TEST_SHOP
        assert "branches" in details
        assert len(details["branches"]) == 1
        assert "sms_sent_count" in details
        print("[PASS] get_shop_details_for_super_admin succeeded")

        # 7. Delete Branch
        del_res = await delete_branch(branch_id, admin_id)
        assert del_res["message"] == "Branch deactivated successfully"
        print("[PASS] delete_branch succeeded")

    finally:
        # Cleanup
        await test_admin.delete()
        await Branch.find(Branch.shop_name == TEST_SHOP).delete()
        print("[PASS] Cleaned up test data")

    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_tests())
