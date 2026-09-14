from fastapi import APIRouter, Depends
from model.Stakeholder import Stakeholder
from middleware.auth import get_current_stakeholder, require_roles
from schema.subscription import PackageUpgradeRequest, PackageEntitlementsResponse
from repository.subscription import SubscriptionService

subscription_router = APIRouter(prefix="/api/v1/subscription", tags=["Subscriptions & Packages"])


@subscription_router.get("/entitlements", response_model=PackageEntitlementsResponse)
async def get_entitlements(
    current_user: Stakeholder = Depends(get_current_stakeholder)
):
    return await SubscriptionService.get_entitlements(current_user.worker_shop_name)


@subscription_router.post("/upgrade")
async def upgrade_package(
    payload: PackageUpgradeRequest,
    current_user: Stakeholder = Depends(require_roles(["owner", "admin"]))
):
    return await SubscriptionService.upgrade_package(
        payload=payload,
        shop_name=current_user.worker_shop_name
    )
