from model.Inventory import Inventory
from model.Category import Category
from schema.inventory import InventoryCreate, InventoryUpdate, BulkImportRowResult, BulkImportResponse # noqa
from beanie import PydanticObjectId
from model.Stakeholder import Stakeholder
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
import csv
import io


async def _resolve_category(category_id: str | None) -> Category | None:
    if not category_id:
        return None
    category = await Category.get(PydanticObjectId(category_id))
    if not category or category.is_deleted:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


async def add_to_shop_inventory(payload: InventoryCreate, admin: str):
    worker_admin = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(admin))  # noqa
    if not worker_admin:
        return {"message": "Unauthorized to add inventory items"}  # noqa
    worker_admin_shop_name = worker_admin.worker_shop_name

    category = await _resolve_category(payload.category_id)

    new_inventory_item = Inventory(
        product_name=payload.product_name,
        product_price=payload.product_price,
        amount_available=payload.amount_available,
        sku=payload.sku or None,
        created_by=admin,
        worker_shop_name=worker_admin_shop_name,
        category_id=str(category.id) if category else None,
        category_name=category.name if category else None,
    )
    try:
        await new_inventory_item.insert()
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Another product in this shop already uses that SKU") # noqa
    return {
        "message": "Inventory item added successfully",
        "inventory_id": str(new_inventory_item.id),
    }


async def get_all_inventory_items_for_shop(worker_id: str):
    worker = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(worker_id))  # noqa
    if not worker:
        return {"message": "Unauthorized to view inventory items"}  # noqa
    items = await Inventory.find(Inventory.worker_shop_name == worker.worker_shop_name, Inventory.is_deleted == False).to_list() # noqa
    return items


async def update_inventory_item(inventory_id: str, payload: InventoryUpdate, admin: str): # noqa
    admin_record = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(admin))  # noqa
    if not admin_record:
        raise HTTPException(status_code=403, detail="Unauthorized")

    item = await Inventory.get(PydanticObjectId(inventory_id))
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    if item.worker_shop_name != admin_record.worker_shop_name:
        raise HTTPException(status_code=403, detail="Item does not belong to your shop")  # noqa

    update_data = payload.model_dump(exclude_none=True)

    if "category_id" in update_data:
        category = await _resolve_category(update_data.pop("category_id"))
        item.category_id = str(category.id) if category else None
        item.category_name = category.name if category else None

    if "amount_available" in update_data:
        item.amount_available = update_data.pop("amount_available")
        item.is_available = item.amount_available > 0

    for field, value in update_data.items():
        setattr(item, field, value)

    try:
        await item.save()
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Another product in this shop already uses that SKU") # noqa
    return {"message": "Inventory item updated successfully", "item": item}


async def delete_inventory_item(inventory_id: str, admin: str):
    admin_record = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(admin))  # noqa
    if not admin_record:
        raise HTTPException(status_code=403, detail="Unauthorized")

    item = await Inventory.get(PydanticObjectId(inventory_id))
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    if item.worker_shop_name != admin_record.worker_shop_name:
        raise HTTPException(status_code=403, detail="Item does not belong to your shop")  # noqa

    item.is_deleted = True
    await item.save()
    return {"message": "Inventory item deleted successfully"}


REQUIRED_BULK_COLUMNS = {"product_name", "product_price", "amount_available"}


async def bulk_import_inventory(file_bytes: bytes, admin: str) -> BulkImportResponse:
    worker_admin = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(admin))  # noqa
    if not worker_admin:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded CSV") # noqa

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not REQUIRED_BULK_COLUMNS.issubset({f.strip() for f in reader.fieldnames}): # noqa
        raise HTTPException(
            status_code=400,
            detail=f"CSV must include columns: {', '.join(sorted(REQUIRED_BULK_COLUMNS))} (optional: sku, category)", # noqa
        )

    categories = await Category.find(Category.is_deleted == False).to_list() # noqa
    category_by_name = {c.name.strip().lower(): c for c in categories}

    results: list[BulkImportRowResult] = []
    created = 0

    for row_number, row in enumerate(reader, start=2):  # header is row 1
        product_name = (row.get("product_name") or "").strip()
        price_raw = (row.get("product_price") or "").strip()
        amount_raw = (row.get("amount_available") or "").strip()
        sku = (row.get("sku") or "").strip() or None
        category_name = (row.get("category") or "").strip()

        if not product_name:
            results.append(BulkImportRowResult(row=row_number, status="skipped", reason="Missing product_name")) # noqa
            continue

        try:
            price = float(price_raw)
            amount = int(amount_raw)
        except ValueError:
            results.append(BulkImportRowResult(
                row=row_number, status="skipped", product_name=product_name,
                reason="product_price/amount_available must be numeric",
            ))
            continue

        if price < 0 or amount < 0:
            results.append(BulkImportRowResult(
                row=row_number, status="skipped", product_name=product_name,
                reason="product_price/amount_available cannot be negative",
            ))
            continue

        category = category_by_name.get(category_name.lower()) if category_name else None

        item = Inventory(
            product_name=product_name,
            product_price=price,
            amount_available=amount,
            sku=sku,
            created_by=admin,
            worker_shop_name=worker_admin.worker_shop_name,
            category_id=str(category.id) if category else None,
            category_name=category.name if category else None,
        )

        try:
            await item.insert()
        except DuplicateKeyError:
            results.append(BulkImportRowResult(
                row=row_number, status="skipped", product_name=product_name,
                reason=f"SKU '{sku}' already exists in this shop",
            ))
            continue

        reason = None
        if category_name and not category:
            reason = f"Category '{category_name}' not found — added without a category" # noqa
        results.append(BulkImportRowResult(row=row_number, status="created", product_name=product_name, reason=reason)) # noqa
        created += 1

    return BulkImportResponse(
        total_rows=len(results),
        created=created,
        skipped=len(results) - created,
        results=results,
    )
