from datetime import datetime, timezone
from fastapi import HTTPException
from model.Subscription import Subscription, PackageTier
from model.Branch import Branch
from model.Stakeholder import Stakeholder
from model.Inventory import Inventory
from schema.subscription import PackageUpgradeRequest, PackageEntitlementsResponse


TIER_LIMITS = {
    "START-UP": {
        "max_branches": 1,
        "max_users": 3,
        "max_products": 500,
        "allow_advanced_reports": False,
        "allow_custom_branding": False,
        "allow_bulk_import": True,
        "allow_api_access": False,
    },
    "ELITE": {
        "max_branches": 5,
        "max_users": 15,
        "max_products": 5000,
        "allow_advanced_reports": True,
        "allow_custom_branding": True,
        "allow_bulk_import": True,
        "allow_api_access": False,
    },
    "ENTERPRISE": {
        "max_branches": 50,
        "max_users": 100,
        "max_products": 50000,
        "allow_advanced_reports": True,
        "allow_custom_branding": True,
        "allow_bulk_import": True,
        "allow_api_access": True,
    },
}


class SubscriptionService:
    @staticmethod
    async def get_or_create_subscription(shop_name: str) -> Subscription:
        sub = await Subscription.find_one(Subscription.shop_name == shop_name)
        if not sub:
            limits = TIER_LIMITS["START-UP"]
            sub = Subscription(
                shop_name=shop_name,
                package_tier="START-UP",
                status="ACTIVE",
                **limits,
                created_at=datetime.now(timezone.utc),
            )
            await sub.insert()
        return sub

    @staticmethod
    async def get_entitlements(shop_name: str) -> PackageEntitlementsResponse:
        sub = await SubscriptionService.get_or_create_subscription(shop_name)
        branch_count = await Branch.find(Branch.shop_name == shop_name, Branch.is_active == True).count()
        user_count = await Stakeholder.find(Stakeholder.worker_shop_name == shop_name, Stakeholder.is_active == True).count()
        product_count = await Inventory.find(Inventory.worker_shop_name == shop_name, Inventory.is_deleted == False).count()

        return PackageEntitlementsResponse(
            shop_name=shop_name,
            package_tier=sub.package_tier,
            status=sub.status,
            max_branches=sub.max_branches,
            max_users=sub.max_users,
            max_products=sub.max_products,
            allow_advanced_reports=sub.allow_advanced_reports,
            allow_custom_branding=sub.allow_custom_branding,
            allow_bulk_import=sub.allow_bulk_import,
            allow_api_access=sub.allow_api_access,
            current_branch_count=branch_count,
            current_user_count=user_count,
            current_product_count=product_count,
        )

    @staticmethod
    async def upgrade_package(payload: PackageUpgradeRequest, shop_name: str) -> Subscription:
        tier = payload.package_tier
        if tier not in TIER_LIMITS:
            raise HTTPException(status_code=400, detail="Invalid package tier")

        sub = await SubscriptionService.get_or_create_subscription(shop_name)
        limits = TIER_LIMITS[tier]

        sub.package_tier = tier
        sub.max_branches = limits["max_branches"]
        sub.max_users = limits["max_users"]
        sub.max_products = limits["max_products"]
        sub.allow_advanced_reports = limits["allow_advanced_reports"]
        sub.allow_custom_branding = limits["allow_custom_branding"]
        sub.allow_bulk_import = limits["allow_bulk_import"]
        sub.allow_api_access = limits["allow_api_access"]
        sub.status = "ACTIVE"
        await sub.save()

        return sub
