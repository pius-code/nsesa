# repository/reports.py
from datetime import datetime, timedelta, timezone
from io import BytesIO
from beanie import PydanticObjectId
from beanie.operators import In
from fastapi import HTTPException
from model.Transaction import Transaction
from model.TransactionAudit import TransactionAudit
from schema.report import (
    FinancialReportResponse,
    ReportMetricItem,
    PaymentMethodBreakdown,
    DailyTrendPoint,
)

# ReportLab imports for PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

NOT_DELETED = {"$or": [{"is_deleted": False}, {"is_deleted": None}]}


async def _run_aggregation(pipeline: list) -> list:
    collection = Transaction.get_pymongo_collection()
    cursor = collection.aggregate(pipeline)
    return await cursor.to_list(length=None)


def _parse_dates(
    period: str, start_date: str | None = None, end_date: str | None = None
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "custom" and start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
            return start_dt, end_dt
        except ValueError:
            raise HTTPException(status_code=400, detail="Dates must be formatted as YYYY-MM-DD")

    if period == "monthly":
        # 1st day of current month to end of today
        start_dt = today_start.replace(day=1)
        end_dt = today_start + timedelta(days=1)
        return start_dt, end_dt

    # Default to "weekly" (rolling 7 days)
    start_dt = today_start - timedelta(days=6)
    end_dt = today_start + timedelta(days=1)
    return start_dt, end_dt


async def get_financial_report(
    shop_name: str,
    period: str = "weekly",
    start_date: str | None = None,
    end_date: str | None = None,
) -> FinancialReportResponse:
    start_dt, end_dt = _parse_dates(period, start_date, end_date)

    match_filter = {
        "at_shop": shop_name,
        "status": "success",
        "created_at": {"$gte": start_dt, "$lt": end_dt},
        **NOT_DELETED,
    }

    # 1. Overall Revenue, COGS, and Profit
    summary_pipeline = [
        {"$match": match_filter},
        {"$unwind": {"path": "$items", "preserveNullAndEmptyArrays": True}},
        {
            "$group": {
                "_id": "$_id",
                "total_price": {"$first": "$total_price"},
                "item_cogs": {
                    "$sum": {
                        "$multiply": [
                            {"$ifNull": ["$items.unit_cost", 0.0]},
                            {"$ifNull": ["$items.quantity", 0]},
                        ]
                    }
                },
            }
        },
        {
            "$group": {
                "_id": None,
                "total_revenue": {"$sum": "$total_price"},
                "total_cogs": {"$sum": "$item_cogs"},
                "total_transactions": {"$sum": 1},
            }
        },
    ]

    summary_rows = await _run_aggregation(summary_pipeline)
    if summary_rows:
        total_revenue = float(summary_rows[0]["total_revenue"] or 0.0)
        total_cogs = float(summary_rows[0]["total_cogs"] or 0.0)
        total_transactions = int(summary_rows[0]["total_transactions"] or 0)
    else:
        total_revenue = 0.0
        total_cogs = 0.0
        total_transactions = 0

    gross_profit = total_revenue - total_cogs
    profit_margin_pct = (
        round((gross_profit / total_revenue) * 100, 2) if total_revenue > 0 else 0.0
    )
    avg_tx_value = (
        round(total_revenue / total_transactions, 2) if total_transactions > 0 else 0.0
    )

    # 2. Product Profitability Breakdown
    product_pipeline = [
        {"$match": match_filter},
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$items.product_id",
                "product_name": {"$first": "$items.product_name"},
                "quantity_sold": {"$sum": "$items.quantity"},
                "revenue": {"$sum": "$items.subtotal"},
                "cogs": {
                    "$sum": {
                        "$multiply": [
                            {"$ifNull": ["$items.unit_cost", 0.0]},
                            "$items.quantity",
                        ]
                    }
                },
            }
        },
        {
            "$project": {
                "product_name": 1,
                "quantity_sold": 1,
                "revenue": 1,
                "cogs": 1,
                "profit": {"$subtract": ["$revenue", "$cogs"]},
                "margin_pct": {
                    "$cond": [
                        {"$gt": ["$revenue", 0]},
                        {
                            "$multiply": [
                                {
                                    "$divide": [
                                        {"$subtract": ["$revenue", "$cogs"]},
                                        "$revenue",
                                    ]
                                },
                                100,
                            ]
                        },
                        0,
                    ]
                },
            }
        },
        {"$sort": {"profit": -1}},
        {"$limit": 10},
    ]

    product_rows = await _run_aggregation(product_pipeline)
    top_products = [
        ReportMetricItem(
            product_id=str(row["_id"]),
            product_name=row["product_name"],
            quantity_sold=row["quantity_sold"],
            revenue=round(row["revenue"], 2),
            cogs=round(row["cogs"], 2),
            profit=round(row["profit"], 2),
            margin_pct=round(row["margin_pct"], 2),
        )
        for row in product_rows
    ]

    # 3. Payment Method Breakdown
    payment_pipeline = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": "$payment_mode",
                "total": {"$sum": "$total_price"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"total": -1}},
    ]
    payment_rows = await _run_aggregation(payment_pipeline)
    payment_breakdown = [
        PaymentMethodBreakdown(
            payment_mode=row["_id"] or "unspecified",
            total=round(row["total"], 2),
            count=row["count"],
        )
        for row in payment_rows
    ]

    # 4. Daily Trends Curve
    daily_pipeline = [
        {"$match": match_filter},
        {"$unwind": {"path": "$items", "preserveNullAndEmptyArrays": True}},
        {
            "$group": {
                "_id": {
                    "date": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$created_at",
                        }
                    },
                    "tx_id": "$_id",
                },
                "tx_total": {"$first": "$total_price"},
                "item_cogs": {
                    "$sum": {
                        "$multiply": [
                            {"$ifNull": ["$items.unit_cost", 0.0]},
                            {"$ifNull": ["$items.quantity", 0]},
                        ]
                    }
                },
            }
        },
        {
            "$group": {
                "_id": "$_id.date",
                "revenue": {"$sum": "$tx_total"},
                "cogs": {"$sum": "$item_cogs"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    daily_rows = await _run_aggregation(daily_pipeline)
    daily_trends = [
        DailyTrendPoint(
            date=row["_id"],
            revenue=round(row["revenue"], 2),
            cogs=round(row["cogs"], 2),
            profit=round(row["revenue"] - row["cogs"], 2),
            count=row["count"],
        )
        for row in daily_rows
    ]

    # 5. Refunds & Pending Tabs in Period
    refund_entries = await TransactionAudit.find(
        TransactionAudit.action == "refunded",
        TransactionAudit.at_shop == shop_name,
        TransactionAudit.created_at >= start_dt,
        TransactionAudit.created_at < end_dt,
    ).to_list()
    refund_value = 0.0
    if refund_entries:
        refund_tx_ids = [PydanticObjectId(e.transaction_id) for e in refund_entries]
        refunded_txs = await Transaction.find(In(Transaction.id, refund_tx_ids)).to_list()
        refund_value = sum(t.total_price for t in refunded_txs)

    pending_pipeline = [
        {
            "$match": {
                "at_shop": shop_name,
                "status": "pending",
                "created_at": {"$gte": start_dt, "$lt": end_dt},
                **NOT_DELETED,
            }
        },
        {
            "$group": {
                "_id": None,
                "value": {"$sum": "$total_price"},
                "count": {"$sum": 1},
            }
        },
    ]
    pending_result = await _run_aggregation(pending_pipeline)
    pending_count = pending_result[0]["count"] if pending_result else 0
    pending_value = pending_result[0]["value"] if pending_result else 0.0

    return FinancialReportResponse(
        period=period,
        start_date=start_dt.strftime("%Y-%m-%d"),
        end_date=(end_dt - timedelta(days=1)).strftime("%Y-%m-%d"),
        shop_name=shop_name,
        total_revenue=round(total_revenue, 2),
        total_cogs=round(total_cogs, 2),
        gross_profit=round(gross_profit, 2),
        profit_margin_pct=profit_margin_pct,
        total_transactions=total_transactions,
        avg_transaction_value=avg_tx_value,
        refund_count=len(refund_entries),
        refund_value=round(refund_value, 2),
        pending_tabs_count=pending_count,
        pending_tabs_value=round(pending_value, 2),
        top_profitable_products=top_products,
        payment_breakdown=payment_breakdown,
        daily_trends=daily_trends,
    )


def generate_pdf_report(report: FinancialReportResponse) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748B"),
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=12,
        spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )
    header_cell_style = ParagraphStyle(
        "TableHeaderCell",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
    )

    elements = []

    # Header section
    elements.append(Paragraph(f"{report.shop_name} — Financial & Profit Report", title_style))
    elements.append(
        Paragraph(
            f"Period: <b>{report.period.upper()}</b> ({report.start_date} to {report.end_date}) &nbsp;|&nbsp; Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            subtitle_style,
        )
    )
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceAfter=12))

    # Executive Summary Grid Card
    summary_data = [
        [
            Paragraph("<b>Total Revenue</b>", header_cell_style),
            Paragraph("<b>Cost of Goods (COGS)</b>", header_cell_style),
            Paragraph("<b>Gross Profit</b>", header_cell_style),
            Paragraph("<b>Profit Margin</b>", header_cell_style),
        ],
        [
            Paragraph(f"GHS {report.total_revenue:,.2f}", title_style),
            Paragraph(f"GHS {report.total_cogs:,.2f}", cell_style),
            Paragraph(f"<b>GHS {report.gross_profit:,.2f}</b>", title_style),
            Paragraph(f"<b>{report.profit_margin_pct:.1f}%</b>", title_style),
        ],
        [
            Paragraph("<b>Transactions</b>", header_cell_style),
            Paragraph("<b>Avg Order Value</b>", header_cell_style),
            Paragraph("<b>Refunds Total</b>", header_cell_style),
            Paragraph("<b>Pending Tabs</b>", header_cell_style),
        ],
        [
            Paragraph(f"{report.total_transactions}", cell_style),
            Paragraph(f"GHS {report.avg_transaction_value:,.2f}", cell_style),
            Paragraph(f"GHS {report.refund_value:,.2f} ({report.refund_count})", cell_style),
            Paragraph(f"GHS {report.pending_tabs_value:,.2f} ({report.pending_tabs_count})", cell_style),
        ],
    ]

    summary_table = Table(summary_data, colWidths=[130, 130, 140, 140])
    summary_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    elements.append(summary_table)
    elements.append(Spacer(1, 14))

    # Top Profitable Products Table
    elements.append(Paragraph("Top Profitable Products", section_heading))
    if report.top_profitable_products:
        prod_data = [[
            Paragraph("<b>Product Name</b>", header_cell_style),
            Paragraph("<b>Qty Sold</b>", header_cell_style),
            Paragraph("<b>Revenue</b>", header_cell_style),
            Paragraph("<b>COGS</b>", header_cell_style),
            Paragraph("<b>Profit</b>", header_cell_style),
            Paragraph("<b>Margin %</b>", header_cell_style),
        ]]
        for p in report.top_profitable_products:
            prod_data.append([
                Paragraph(p.product_name, cell_style),
                Paragraph(str(p.quantity_sold), cell_style),
                Paragraph(f"GHS {p.revenue:,.2f}", cell_style),
                Paragraph(f"GHS {p.cogs:,.2f}", cell_style),
                Paragraph(f"<b>GHS {p.profit:,.2f}</b>", cell_style),
                Paragraph(f"{p.margin_pct:.1f}%", cell_style),
            ])

        prod_table = Table(prod_data, colWidths=[170, 60, 80, 80, 80, 70])
        prod_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        elements.append(prod_table)
    else:
        elements.append(Paragraph("No products sold in this period.", cell_style))

    elements.append(Spacer(1, 14))

    # Payment Method Breakdown Table
    elements.append(Paragraph("Payment Method Breakdown", section_heading))
    if report.payment_breakdown:
        pay_data = [[
            Paragraph("<b>Payment Mode</b>", header_cell_style),
            Paragraph("<b>Transaction Count</b>", header_cell_style),
            Paragraph("<b>Total Volume</b>", header_cell_style),
        ]]
        for pay in report.payment_breakdown:
            pay_data.append([
                Paragraph(pay.payment_mode.upper(), cell_style),
                Paragraph(str(pay.count), cell_style),
                Paragraph(f"GHS {pay.total:,.2f}", cell_style),
            ])

        pay_table = Table(pay_data, colWidths=[200, 150, 190])
        pay_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        elements.append(pay_table)
    else:
        elements.append(Paragraph("No payment data recorded in this period.", cell_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
