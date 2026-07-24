# repository/dashboard.py
from datetime import datetime, timedelta, timezone
from beanie import PydanticObjectId
from beanie.operators import In
from model.Transaction import Transaction
from model.TransactionAudit import TransactionAudit
from model.Inventory import Inventory
from schema.dashboard import DashboardOverview

LOW_STOCK_THRESHOLD = 5

# Matches both {is_deleted: false} and documents missing the field entirely
# — see the same note in repository/transaction.py for why this is needed.
NOT_DELETED = {"$or": [{"is_deleted": False}, {"is_deleted": None}]}


def _day_start(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


async def _run_aggregation(pipeline: list) -> list:
    # Beanie 2.0.1's Document.aggregate() awaits the motor cursor's
    # .aggregate() call as if it were pymongo's native async driver, but
    # motor's .aggregate() returns a cursor synchronously (no await) — the
    # two are incompatible, so we drive the raw motor collection ourselves. # noqa
    collection = Transaction.get_pymongo_collection()
    cursor = collection.aggregate(pipeline)
    return await cursor.to_list(length=None)


async def _revenue_and_count(shop_name: str, start: datetime, end: datetime | None = None): # noqa
    created_at_filter = {"$gte": start}
    if end:
        created_at_filter["$lt"] = end

    pipeline = [
        {"$match": {
            "at_shop": shop_name,
            "status": "success",
            "created_at": created_at_filter,
            **NOT_DELETED,
        }},
        {"$group": {"_id": None, "revenue": {"$sum": "$total_price"}, "count": {"$sum": 1}}}, # noqa
    ]
    result = await _run_aggregation(pipeline)
    if not result:
        return 0.0, 0
    return result[0]["revenue"], result[0]["count"]


async def get_dashboard_overview(shop_name: str) -> DashboardOverview:
    now = datetime.now(timezone.utc)
    today_start = _day_start(now)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=6)  # rolling 7 days incl. today
    prev_week_start = week_start - timedelta(days=7)

    today_revenue, today_count = await _revenue_and_count(shop_name, today_start) # noqa
    yesterday_revenue, _ = await _revenue_and_count(shop_name, yesterday_start, today_start) # noqa
    week_revenue, week_count = await _revenue_and_count(shop_name, week_start)
    previous_week_revenue, _ = await _revenue_and_count(shop_name, prev_week_start, week_start) # noqa

    payment_pipeline = [
        {"$match": {
            "at_shop": shop_name, "status": "success",
            "created_at": {"$gte": today_start}, **NOT_DELETED,
        }},
        {"$group": {"_id": "$payment_mode", "total": {"$sum": "$total_price"}, "count": {"$sum": 1}}}, # noqa
        {"$sort": {"total": -1}},
    ]
    payment_rows = await _run_aggregation(payment_pipeline)
    payment_breakdown = [
        {"payment_mode": row["_id"] or "unspecified", "total": row["total"], "count": row["count"]} # noqa
        for row in payment_rows
    ]

    top_products_pipeline = [
        {"$match": {
            "at_shop": shop_name, "status": "success",
            "created_at": {"$gte": week_start}, **NOT_DELETED,
        }},
        {"$unwind": "$items"},
        {"$group": {
            "_id": "$items.product_id",
            "product_name": {"$first": "$items.product_name"},
            "quantity_sold": {"$sum": "$items.quantity"},
            "revenue": {"$sum": "$items.subtotal"},
        }},
        {"$sort": {"revenue": -1}},
        {"$limit": 5},
    ]
    top_rows = await _run_aggregation(top_products_pipeline)
    top_products = [
        {
            "product_id": row["_id"],
            "product_name": row["product_name"],
            "quantity_sold": row["quantity_sold"],
            "revenue": row["revenue"],
        }
        for row in top_rows
    ]

    refund_entries = await TransactionAudit.find(
        TransactionAudit.action == "refunded",
        TransactionAudit.at_shop == shop_name,
        TransactionAudit.created_at >= today_start,
    ).to_list()
    refund_value = 0.0
    if refund_entries:
        refund_tx_ids = [PydanticObjectId(e.transaction_id) for e in refund_entries] # noqa
        refunded_txs = await Transaction.find(In(Transaction.id, refund_tx_ids)).to_list() # noqa
        refund_value = sum(t.total_price for t in refunded_txs)

    low_stock = await Inventory.find(
        Inventory.worker_shop_name == shop_name,
        Inventory.is_deleted == False, # noqa
        Inventory.amount_available < LOW_STOCK_THRESHOLD,
    ).sort(Inventory.amount_available).to_list() # noqa

    return DashboardOverview(
        today_revenue=today_revenue,
        today_transaction_count=today_count,
        today_avg_transaction=(today_revenue / today_count) if today_count else 0.0, # noqa
        yesterday_revenue=yesterday_revenue,
        week_revenue=week_revenue,
        week_transaction_count=week_count,
        previous_week_revenue=previous_week_revenue,
        today_refund_count=len(refund_entries),
        today_refund_value=refund_value,
        payment_breakdown_today=payment_breakdown, # type: ignore
        top_products_week=top_products, # type: ignore
        low_stock_items=[
            {"id": str(i.id), "product_name": i.product_name, "amount_available": i.amount_available} # noqa
            for i in low_stock
        ], # type: ignore
    )
