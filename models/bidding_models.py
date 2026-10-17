from pydantic import BaseModel
from typing import Optional


class BiddingStrategyDetailsRequest(BaseModel):
    customer_id: str
    campaign_id: str


class BiddingStrategiesRequest(BaseModel):
    customer_id: str
    strategy_type: Optional[str] = None
