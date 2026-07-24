from pydantic import BaseModel
from typing import List


class PaymentBreakdownEntry(BaseModel):
    payment_mode: str
    total: float
    count: int


class TopProductEntry(BaseModel):
    product_id: str
    product_name: str
    quantity_sold: int
    revenue: float


class LowStockEntry(BaseModel):
    id: str
    product_name: str
    amount_available: int


class DashboardOverview(BaseModel):
    today_revenue: float
    today_transaction_count: int
    today_avg_transaction: float
    yesterday_revenue: float
    week_revenue: float
    week_transaction_count: int
    previous_week_revenue: float
    today_refund_count: int
    today_refund_value: float
    payment_breakdown_today: List[PaymentBreakdownEntry]
    top_products_week: List[TopProductEntry]
    low_stock_items: List[LowStockEntry]
