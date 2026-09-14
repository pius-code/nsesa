from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class StockAdjustmentRequest(BaseModel):
    product_id: str
    quantity_change: int = Field(..., example=10)  # can be positive or negative
    movement_type: Literal["RESTOCK", "ADJUSTMENT", "DAMAGE", "AUDIT"] = "ADJUSTMENT"
    reason: str = Field(..., min_length=3, example="Monthly physical inventory recount")
    branch_name: Optional[str] = None


class StockTransferRequest(BaseModel):
    product_id: str
    from_branch: str
    to_branch: str
    quantity: int = Field(..., gt=0, example=5)
    reason: Optional[str] = Field(None, example="Rebalancing stock between branches")


class BulkProductRow(BaseModel):
    product_name: str
    selling_price: float
    cost_price: Optional[float] = 0.0
    stock_quantity: int = 0
    sku: Optional[str] = None
    barcode: Optional[str] = None
    category_name: Optional[str] = None
    supplier_name: Optional[str] = None
    supplier_contact: Optional[str] = None
    min_stock_level: Optional[int] = 5
    reorder_threshold: Optional[int] = 10


class BulkProductImportRequest(BaseModel):
    products: List[BulkProductRow]
    branch_name: Optional[str] = "Main Branch"
