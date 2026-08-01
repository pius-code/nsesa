from pydantic import BaseModel, Field


class BroadcastSmsRequest(BaseModel):
    message: str = Field(..., min_length=3, max_length=459, example="20% off all drinks this weekend only!") # noqa
