from pydantic import BaseModel
from typing import Optional


class SearchCampaignRequest(
    BaseModel
):
    account_name: str

    customer_id: str

    campaign_name: str

    objective: str

    daily_budget: float

    currency: str

    language: str

    locations: str

    network: str

    bidding_strategy: str

    start_date: Optional[str] = None

    end_date: Optional[str] = None

    status: str

    label: Optional[str] = None
