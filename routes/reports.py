# routes/reports.py
from fastapi import APIRouter, Depends, Query, Response
from middleware.auth import admin_protected_route
from repository.stakeholder import get_stakeholder_worker_shop_name
from repository.reports import get_financial_report, generate_pdf_report
from schema.report import FinancialReportResponse

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/summary", response_model=FinancialReportResponse)
async def get_report_summary(
    period: str = Query(default="weekly", description="weekly | monthly | custom"),
    start_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    admin_id: str = Depends(admin_protected_route),
):
    """Admin only — financial report summary with gross profit and margin metrics"""
    shop_name = await get_stakeholder_worker_shop_name(admin_id)
    if not shop_name:
        return Response(status_code=400, content="Shop not found")
    return await get_financial_report(
        shop_name=shop_name,
        period=period,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/pdf")
async def download_report_pdf(
    period: str = Query(default="weekly", description="weekly | monthly | custom"),
    start_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    admin_id: str = Depends(admin_protected_route),
):
    """Admin only — downloadable PDF financial report"""
    shop_name = await get_stakeholder_worker_shop_name(admin_id)
    if not shop_name:
        return Response(status_code=400, content="Shop not found")

    report_data = await get_financial_report(
        shop_name=shop_name,
        period=period,
        start_date=start_date,
        end_date=end_date,
    )

    pdf_bytes = generate_pdf_report(report_data)
    filename = f"financial-report-{period}-{shop_name.lower().replace(' ', '-')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )
