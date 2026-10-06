from fastapi import APIRouter

from services.search_campaign_service import (
    SearchCampaignService,
)

router = APIRouter(
    prefix="/campaigns/search",
    tags=["Search Campaigns"],
)


@router.get("/health")
def search_health():

    return SearchCampaignService.health()
