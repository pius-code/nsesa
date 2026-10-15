from fastapi import APIRouter, Depends, Query
from repository.dashboard import get_dashboard_overview
from repository.stakeholder import get_stakeholder_worker_shop_name
from middleware.auth import admin_protected_route

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/overview")
async def dashboard_overview(
    branch_name: str | None = Query(default=None, description="Optional branch filter for central auditing"),
    admin=Depends(admin_protected_route),
):
    """Admin only — today/week revenue trends, payment mix, top products, low stock, refunds (collective or per-branch)"""
    shop_name = await get_stakeholder_worker_shop_name(admin)
    return await get_dashboard_overview(shop_name, branch_name=branch_name)
