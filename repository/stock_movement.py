from datetime import datetime, timezone
from fastapi import HTTPException
from beanie import PydanticObjectId
from beanie.operators import In
from model.Inventory import Inventory
from model.StockMovement import StockMovement, StockMovementType
from schema.stock_movement import StockAdjustmentRequest, StockTransferRequest, BulkProductImportRequest
from utils.logger import logger


class StockMovementService:
    @staticmethod
    async def record_movement(
        product_id: str,
        product_name: str,
        shop_name: str,
        movement_type: StockMovementType,
        quantity_change: int,
        previous_quantity: int,
        new_quantity: int,
        performed_by_id: str,
        performed_by_name: str,
        sku: str | None = None,
        branch_name: str | None = "Main Branch",
        unit_cost: float = 0.0,
        unit_price: float = 0.0,
        reference_id: str | None = None,
        reason: str | None = None,
    ) -> StockMovement:
        movement = StockMovement(
            product_id=product_id,
            product_name=product_name,
            sku=sku,
            shop_name=shop_name,
            branch_name=branch_name,
            movement_type=movement_type,
            quantity_change=quantity_change,
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            unit_cost=unit_cost,
            unit_price=unit_price,
            reference_id=reference_id,
            performed_by_id=performed_by_id,
            performed_by_name=performed_by_name,
            reason=reason,
            created_at=datetime.now(timezone.utc),
        )
        await movement.insert()
        return movement

    @staticmethod
    async def adjust_stock(
        payload: StockAdjustmentRequest,
        shop_name: str,
        user_id: str,
        user_name: str,
    ) -> dict:
        try:
            item = await Inventory.get(PydanticObjectId(payload.product_id))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid product ID format")

        if not item or item.worker_shop_name != shop_name or item.is_deleted:
            raise HTTPException(status_code=404, detail="Product not found in inventory")

        prev_qty = item.amount_available
        new_qty = prev_qty + payload.quantity_change
        if new_qty < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Adjustment would result in negative stock ({new_qty}). Current stock is {prev_qty}."
            )

        item.amount_available = new_qty
        item.is_available = new_qty > 0
        await item.save()

        await StockMovementService.record_movement(
            product_id=str(item.id),
            product_name=item.product_name,
            sku=item.sku or item.barcode,
            shop_name=shop_name,
            branch_name=payload.branch_name or item.branch_name or "Main Branch",
            movement_type=payload.movement_type,
            quantity_change=payload.quantity_change,
            previous_quantity=prev_qty,
            new_quantity=new_qty,
            unit_cost=item.cost_price,
            unit_price=item.product_price,
            performed_by_id=user_id,
            performed_by_name=user_name,
            reason=payload.reason,
        )

        return {
            "message": "Stock adjusted successfully",
            "product_id": str(item.id),
            "product_name": item.product_name,
            "previous_quantity": prev_qty,
            "new_quantity": new_qty,
        }

    @staticmethod
    async def transfer_stock(
        payload: StockTransferRequest,
        shop_name: str,
        user_id: str,
        user_name: str,
    ) -> dict:
        try:
            item = await Inventory.get(PydanticObjectId(payload.product_id))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid product ID format")

        if not item or item.worker_shop_name != shop_name or item.is_deleted:
            raise HTTPException(status_code=404, detail="Product not found")

        if item.amount_available < payload.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock to transfer. Only {item.amount_available} available."
            )

        prev_qty = item.amount_available
        new_qty = prev_qty - payload.quantity
        item.amount_available = new_qty
        item.is_available = new_qty > 0
        await item.save()

        # Record transfer out
        await StockMovementService.record_movement(
            product_id=str(item.id),
            product_name=item.product_name,
            sku=item.sku,
            shop_name=shop_name,
            branch_name=payload.from_branch,
            movement_type="TRANSFER_OUT",
            quantity_change=-payload.quantity,
            previous_quantity=prev_qty,
            new_quantity=new_qty,
            unit_cost=item.cost_price,
            unit_price=item.product_price,
            performed_by_id=user_id,
            performed_by_name=user_name,
            reason=f"Transfer to {payload.to_branch}. {payload.reason or ''}".strip(),
        )

        return {
            "message": f"Successfully transferred {payload.quantity} units from {payload.from_branch} to {payload.to_branch}",
            "remaining_stock": new_qty,
        }

    @staticmethod
    async def get_low_stock_intelligence(shop_name: str) -> dict:
        items = await Inventory.find(
            Inventory.worker_shop_name == shop_name,
            Inventory.is_deleted == False
        ).to_list()

        out_of_stock = []
        low_stock = []
        healthy_stock = []

        for item in items:
            threshold = item.reorder_threshold or 10
            if item.amount_available <= 0:
                out_of_stock.append({
                    "id": str(item.id),
                    "product_name": item.product_name,
                    "sku": item.sku,
                    "amount_available": item.amount_available,
                    "reorder_threshold": threshold,
                    "status": "OUT_OF_STOCK",
                    "action_required": "Immediate restock needed",
                })
            elif item.amount_available <= threshold:
                low_stock.append({
                    "id": str(item.id),
                    "product_name": item.product_name,
                    "sku": item.sku,
                    "amount_available": item.amount_available,
                    "reorder_threshold": threshold,
                    "status": "LOW_STOCK",
                    "action_required": "Reorder recommended",
                })
            else:
                healthy_stock.append({
                    "id": str(item.id),
                    "product_name": item.product_name,
                    "amount_available": item.amount_available,
                })

        return {
            "total_products": len(items),
            "out_of_stock_count": len(out_of_stock),
            "low_stock_count": len(low_stock),
            "healthy_count": len(healthy_stock),
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
        }

    @staticmethod
    async def bulk_import_products(
        payload: BulkProductImportRequest,
        shop_name: str,
        user_id: str,
        user_name: str,
    ) -> dict:
        successful_imports = []
        errors = []

        for idx, row in enumerate(payload.products):
            row_num = idx + 1
            if not row.product_name or not row.product_name.strip():
                errors.append({"row": row_num, "error": "Product name is required"})
                continue
            if row.selling_price < 0:
                errors.append({"row": row_num, "error": "Selling price cannot be negative"})
                continue

            try:
                # Check for duplicate SKU in this shop if SKU provided
                if row.sku:
                    existing = await Inventory.find_one(
                        Inventory.worker_shop_name == shop_name,
                        Inventory.sku == row.sku,
                        Inventory.is_deleted == False
                    )
                    if existing:
                        errors.append({"row": row_num, "error": f"Product with SKU '{row.sku}' already exists ({existing.product_name})"})
                        continue

                new_inv = Inventory(
                    product_name=row.product_name.strip(),
                    product_price=row.selling_price,
                    cost_price=row.cost_price or 0.0,
                    amount_available=row.stock_quantity,
                    min_stock_level=row.min_stock_level or 5,
                    reorder_threshold=row.reorder_threshold or 10,
                    worker_shop_name=shop_name,
                    branch_name=payload.branch_name or "Main Branch",
                    sku=row.sku,
                    barcode=row.barcode,
                    category_name=row.category_name,
                    supplier_name=row.supplier_name,
                    supplier_contact=row.supplier_contact,
                    is_available=row.stock_quantity > 0,
                    created_by=user_name,
                )
                await new_inv.insert()

                # Record initial stock in movement ledger
                if row.stock_quantity > 0:
                    await StockMovementService.record_movement(
                        product_id=str(new_inv.id),
                        product_name=new_inv.product_name,
                        sku=new_inv.sku,
                        shop_name=shop_name,
                        branch_name=payload.branch_name,
                        movement_type="RESTOCK",
                        quantity_change=row.stock_quantity,
                        previous_quantity=0,
                        new_quantity=row.stock_quantity,
                        unit_cost=new_inv.cost_price,
                        unit_price=new_inv.product_price,
                        performed_by_id=user_id,
                        performed_by_name=user_name,
                        reason="Initial bulk catalog import",
                    )

                successful_imports.append({
                    "id": str(new_inv.id),
                    "product_name": new_inv.product_name,
                    "sku": new_inv.sku,
                    "amount_available": new_inv.amount_available,
                })
            except Exception as e:
                logger.error(f"Error importing row {row_num}: {e}")
                errors.append({"row": row_num, "error": str(e)})

        return {
            "total_received": len(payload.products),
            "successful_count": len(successful_imports),
            "failed_count": len(errors),
            "successful_imports": successful_imports,
            "errors": errors,
        }

    @staticmethod
    async def get_movement_history(
        shop_name: str,
        product_id: str | None = None,
        limit: int = 50,
        skip: int = 0
    ) -> list[StockMovement]:
        query = [StockMovement.shop_name == shop_name]
        if product_id:
            query.append(StockMovement.product_id == product_id)
        return await StockMovement.find(*query).sort(-StockMovement.created_at).skip(skip).limit(limit).to_list()
