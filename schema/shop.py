from pydantic import BaseModel, Field


class ShopStatusRequest(BaseModel):
    reason: str = Field(..., min_length=3, example="Repeated policy violations")
