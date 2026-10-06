from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File

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


@router.post("/from-excel")
async def create_search_from_excel(
    excel_file: UploadFile = File(...)
):

    return {
        "status": "SUCCESS",
        "message": (
            "Excel reçu avec succès."
        ),
        "filename": excel_file.filename,
    }
