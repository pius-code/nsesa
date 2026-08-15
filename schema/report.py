from pydantic import BaseModel, Field
from typing import Optional, List


class ReportMetricItem(BaseModel):
    product_id: Optional[str] = None
    product_name: str
    quantity_sold: int
    revenue: float
    cogs: float
    profit: float
    margin_pct: float


class PaymentMethodBreakdown(BaseModel):
    payment_mode: str
    total: float
    count: int


class DailyTrendPoint(BaseModel):
    date: str  # YYYY-MM-DD
    revenue: float
    cogs: float
    profit: float
    count: int


class FinancialReportResponse(BaseModel):
    period: str  # "weekly" | "monthly" | "custom"
    start_date: str
    end_date: str
    shop_name: str
    total_revenue: float
    total_cogs: float
    gross_profit: float
    profit_margin_pct: float
    total_transactions: int
    avg_transaction_value: float
    refund_count: int
    refund_value: float
    pending_tabs_count: int
    pending_tabs_value: float
    top_profitable_products: List[ReportMetricItem]
    payment_breakdown: List[PaymentMethodBreakdown]
    daily_trends: List[DailyTrendPoint]
