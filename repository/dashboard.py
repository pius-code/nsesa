# repository/dashboard.py
from datetime import datetime, timedelta, timezone
from beanie import PydanticObjectId
from beanie.operators import In
from model.Transaction import Transaction
from model.TransactionAudit import TransactionAudit
from model.Inventory import Inventory
from model.Branch import Branch
from schema.dashboard import DashboardOverview, LowStockEntry

LOW_STOCK_THRESHOLD = 5

# Matches both {is_deleted: false} and documents missing the field entirely
NOT_DELETED = {"$or": [{"is_deleted": False}, {"is_deleted": None}]}


def _day_start(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _combine_match(*parts: dict) -> dict:
    valid = [p for p in parts if p]
    if not valid:
        return {}
    if len(valid) == 1:
        return valid[0]
    return {"$and": valid}


async def _run_aggregation(pipeline: list) -> list:
    collection = Transaction.get_pymongo_collection()
    cursor = collection.aggregate(pipeline)
    return await cursor.to_list(length=None)


async def _build_branch_query(shop_name: str, branch_name: str | None) -> tuple[dict, str]:
    main_branch = await Branch.find_one(
        Branch.shop_name == shop_name, Branch.is_main == True, Branch.is_active == True
    )
    main_branch_name = main_branch.branch_name if main_branch else "Main Branch"

    if not branch_name or branch_name.strip().lower() == "all":
        return {}, main_branch_name

    target = branch_name.strip()
    is_main = target.lower() in ("main", "main branch", main_branch_name.lower())
    if is_main:
        query = {
            "$or": [
                {"branch_name": target},
                {"branch_name": main_branch_name},
                {"branch_name": None},
                {"branch_name": ""},
                {"branch_name": {"$regex": r"^main(\s+branch)?$", "$options": "i"}},
            ]
        }
    else:
        query = {"branch_name": target}

    return query, main_branch_name


async def _revenue_and_count(
    shop_name: str, start: datetime, end: datetime | None = None, branch_query: dict = {}
):
    created_at_filter = {"$gte": start}
    if end:
        created_at_filter["$lt"] = end

    match_stage = _combine_match(
        {"at_shop": shop_name, "status": "success", "created_at": created_at_filter},
        NOT_DELETED,
        branch_query,
    )
    pipeline = [
        {"$match": match_stage},
        {"$group": {"_id": None, "revenue": {"$sum": "$total_price"}, "count": {"$sum": 1}}},
    ]
    result = await _run_aggregation(pipeline)
    if not result:
        return 0.0, 0
    return result[0]["revenue"], result[0]["count"]


async def get_dashboard_overview(shop_name: str, branch_name: str | None = None) -> DashboardOverview:
    now = datetime.now(timezone.utc)
    today_start = _day_start(now)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=6)  # rolling 7 days incl. today
    prev_week_start = week_start - timedelta(days=7)

    branch_query, main_branch_name = await _build_branch_query(shop_name, branch_name)

    today_revenue, today_count = await _revenue_and_count(shop_name, today_start, branch_query=branch_query)
    yesterday_revenue, _ = await _revenue_and_count(shop_name, yesterday_start, today_start, branch_query=branch_query)
    week_revenue, week_count = await _revenue_and_count(shop_name, week_start, branch_query=branch_query)
    previous_week_revenue, _ = await _revenue_and_count(shop_name, prev_week_start, week_start, branch_query=branch_query)

    payment_match = _combine_match(
        {"at_shop": shop_name, "status": "success", "created_at": {"$gte": today_start}},
        NOT_DELETED,
        branch_query,
    )
    payment_pipeline = [
        {"$match": payment_match},
        {"$group": {"_id": "$payment_mode", "total": {"$sum": "$total_price"}, "count": {"$sum": 1}}},
        {"$sort": {"total": -1}},
    ]
    payment_rows = await _run_aggregation(payment_pipeline)
    payment_breakdown = [
        {"payment_mode": row["_id"] or "unspecified", "total": row["total"], "count": row["count"]}
        for row in payment_rows
    ]

    top_products_match = _combine_match(
        {"at_shop": shop_name, "status": "success", "created_at": {"$gte": week_start}},
        NOT_DELETED,
        branch_query,
    )
    top_products_pipeline = [
        {"$match": top_products_match},
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
    refund_count = 0
    if refund_entries:
        refund_tx_ids = [PydanticObjectId(e.transaction_id) for e in refund_entries]
        refunded_txs = await Transaction.find(In(Transaction.id, refund_tx_ids)).to_list()
        if branch_name and branch_name.strip().lower() != "all":
            target = branch_name.strip().lower()
            is_main = target in ("main", "main branch", main_branch_name.lower())
            scoped_txs = []
            for t in refunded_txs:
                t_br = (t.branch_name or "").strip().lower()
                if is_main:
                    if not t_br or t_br in ("main", "main branch", main_branch_name.lower(), target):
                        scoped_txs.append(t)
                else:
                    if t_br == target:
                        scoped_txs.append(t)
            refund_value = sum(t.total_price for t in scoped_txs)
            refund_count = len(scoped_txs)
        else:
            refund_value = sum(t.total_price for t in refunded_txs)
            refund_count = len(refund_entries)

    pending_match = _combine_match(
        {"at_shop": shop_name, "status": "pending"},
        NOT_DELETED,
        branch_query,
    )
    pending_pipeline = [
        {"$match": pending_match},
        {"$group": {"_id": None, "value": {"$sum": "$total_price"}, "count": {"$sum": 1}}},
    ]
    pending_result = await _run_aggregation(pending_pipeline)
    pending_count = pending_result[0]["count"] if pending_result else 0
    pending_value = pending_result[0]["value"] if pending_result else 0.0

    cust_match = _combine_match(
        {"at_shop": shop_name},
        NOT_DELETED,
        branch_query,
    )
    names = await Transaction.get_pymongo_collection().distinct("customer_name", cust_match)
    unique_customers = {n.strip().lower() for n in names if n and n.strip().lower() != "customer"}

    month_start = today_start.replace(day=1)
    month_match = _combine_match(
        {"at_shop": shop_name, "status": {"$ne": "pending"}, "created_at": {"$gte": month_start}},
        NOT_DELETED,
        branch_query,
    )
    month_pipeline = [
        {"$match": month_match},
        {"$count": "count"},
    ]
    month_result = await _run_aggregation(month_pipeline)
    month_completed_count = month_result[0]["count"] if month_result else 0

    all_inventory = await Inventory.find(
        Inventory.worker_shop_name == shop_name,
        Inventory.is_deleted == False,
    ).to_list()

    total_qty_by_name = {}
    for i in all_inventory:
        pname = (i.product_name or "").strip().lower()
        total_qty_by_name[pname] = total_qty_by_name.get(pname, 0) + max(0, i.amount_available)

    target_branch = branch_name.strip().lower() if branch_name and branch_name.strip().lower() != "all" else None
    is_filtering_main = target_branch in ("main", "main branch", main_branch_name.lower()) if target_branch else False

    low_stock = []
    for i in all_inventory:
        if i.amount_available < LOW_STOCK_THRESHOLD:
            pname = (i.product_name or "").strip().lower()
            br = i.branch_name.strip() if i.branch_name else main_branch_name
            if br.lower() in ("main", "main branch"):
                br = main_branch_name

            if target_branch:
                if is_filtering_main:
                    if br.lower() not in (main_branch_name.lower(), target_branch):
                        continue
                else:
                    if br.lower() != target_branch:
                        continue

            low_stock.append(
                LowStockEntry(
                    id=str(i.id),
                    product_name=i.product_name,
                    amount_available=i.amount_available,
                    branch_name=br,
                    total_shop_quantity=total_qty_by_name.get(pname, i.amount_available),
                )
            )
    low_stock.sort(key=lambda x: x.amount_available)

    return DashboardOverview(
        today_revenue=today_revenue,
        today_transaction_count=today_count,
        today_avg_transaction=(today_revenue / today_count) if today_count else 0.0,
        yesterday_revenue=yesterday_revenue,
        week_revenue=week_revenue,
        week_transaction_count=week_count,
        previous_week_revenue=previous_week_revenue,
        today_refund_count=refund_count,
        today_refund_value=refund_value,
        pending_order_count=pending_count,
        pending_order_value=pending_value,
        total_unique_customers=len(unique_customers),
        month_completed_transaction_count=month_completed_count,
        payment_breakdown_today=payment_breakdown,
        top_products_week=top_products,
        low_stock_items=low_stock,
    )
