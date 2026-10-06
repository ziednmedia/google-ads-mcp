from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File
import tempfile

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

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".xlsx"
        ) as temp_file:

            contents = await excel_file.read()

            temp_file.write(
                contents
            )

            temp_path = (
                temp_file.name
            )

        result = (
            SearchCampaignService
            .read_excel(
                temp_path
            )
        )

        return {
            "status":
                "SUCCESS",

            "filename":
                excel_file.filename,

            "data":
                result,
        }

    except Exception as error:

        return {
            "status":
                "FAILED",

            "error":
                str(error),
        }
