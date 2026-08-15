from pydantic import BaseModel, Field
from typing import Optional


class InventoryCreate(BaseModel):
    product_name: str = Field(..., example="Product A")
    product_price: float = Field(..., example=19.99)
    cost_price: Optional[float] = Field(0.0, example=12.50)
    amount_available: int = Field(..., example=100)
    sku: Optional[str] = Field(None, example="SKU-001")
    category_id: Optional[str] = Field(None, example="665f1b2c3a4d5e6f7a8b9c0d")
    supplier_name: Optional[str] = Field(None, example="ABC Wholesale")
    supplier_contact: Optional[str] = Field(None, example="+233240000000")


class InventoryUpdate(BaseModel):
    product_name: Optional[str] = Field(None, example="Product A")
    product_price: Optional[float] = Field(None, example=19.99)
    cost_price: Optional[float] = Field(None, example=12.50)
    amount_available: Optional[int] = Field(None, example=100)
    sku: Optional[str] = Field(None, example="SKU-001")
    category_id: Optional[str] = Field(None, example="665f1b2c3a4d5e6f7a8b9c0d")
    supplier_name: Optional[str] = Field(None, example="ABC Wholesale")
    supplier_contact: Optional[str] = Field(None, example="+233240000000")


class BulkImportRowResult(BaseModel):
    row: int
    status: str  # "created" | "skipped"
    product_name: Optional[str] = None
    reason: Optional[str] = None


class BulkImportResponse(BaseModel):
    total_rows: int
    created: int
    skipped: int
    results: list[BulkImportRowResult]
