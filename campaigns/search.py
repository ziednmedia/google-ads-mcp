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


# ============================================================
# FROM EXCEL
# ============================================================
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
# ============================================================
# END FROM EXCEL
# ============================================================
# ============================================================
# VALIDATE
# ============================================================
@router.post("/validate")
async def validate_search_campaign(
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

        validation_errors = []

        campaign = result.get(
            "campaign",
            {}
        )

        ad_groups = result.get(
            "ad_groups",
            []
        )

        ads = result.get(
            "ads",
            []
        )

        keywords = result.get(
            "keywords",
            []
        )

        sitelinks = result.get(
            "sitelinks",
            []
        )

        # ==================================
        # CAMPAIGN
        # ==================================

        if not campaign.get(
            "campaign_name"
        ):
            validation_errors.append(
                "Campaign name missing"
            )

        if not campaign.get(
            "customer_id"
        ):
            validation_errors.append(
                "Customer ID missing"
            )

        if (
            campaign.get(
                "daily_budget"
            ) is None
            or campaign.get(
                "daily_budget"
            ) <= 0
        ):
            validation_errors.append(
                "Daily budget must be greater than 0"
            )

        # ==================================
        # AD GROUPS
        # ==================================

        if not ad_groups:

            validation_errors.append(
                "At least one ad group is required"
            )

        for ad_group in ad_groups:

            if not ad_group.get(
                "name"
            ):
                validation_errors.append(
                    "An ad group has no name"
                )

            if not ad_group.get(
                "final_url"
            ):
                validation_errors.append(
                    f"{ad_group.get('name')} "
                    "has no Final URL"
                )

        # ==================================
        # RSA
        # ==================================

        for ad in ads:

            if (
                ad.get(
                    "headlines_count",
                    0
                ) < 3
            ):
                validation_errors.append(
                    f"{ad['ad_group_name']} "
                    "must contain at least 3 headlines"
                )

            if (
                ad.get(
                    "headlines_count",
                    0
                ) > 15
            ):
                validation_errors.append(
                    f"{ad['ad_group_name']} "
                    "contains more than 15 headlines"
                )

            if (
                ad.get(
                    "descriptions_count",
                    0
                ) < 2
            ):
                validation_errors.append(
                    f"{ad['ad_group_name']} "
                    "must contain at least 2 descriptions"
                )

            if (
                ad.get(
                    "descriptions_count",
                    0
                ) > 4
            ):
                validation_errors.append(
                    f"{ad['ad_group_name']} "
                    "contains more than 4 descriptions"
                )

        # ==================================
        # KEYWORDS
        # ==================================

        allowed_match_types = {
            "EXACT",
            "PHRASE",
            "BROAD",
        }

        for keyword in keywords:

            match_type = (
                keyword.get(
                    "match_type",
                    ""
                )
                .upper()
                .strip()
            )

            if (
                match_type
                not in allowed_match_types
            ):
                validation_errors.append(
                    f"Invalid match type: "
                    f"{match_type}"
                )

        # ==================================
        # SITELINKS
        # OPTIONAL
        # ==================================

        for sitelink in sitelinks:

            title = (
                sitelink.get(
                    "title"
                ) or ""
            )

            description_1 = (
                sitelink.get(
                    "description_1"
                ) or ""
            )

            description_2 = (
                sitelink.get(
                    "description_2"
                ) or ""
            )

            if len(title) > 25:

                validation_errors.append(
                    f"Sitelink title "
                    f"'{title}' exceeds 25 characters"
                )

            if len(description_1) > 35:

                validation_errors.append(
                    f"Sitelink description 1 "
                    f"exceeds 35 characters"
                )

            if len(description_2) > 35:

                validation_errors.append(
                    f"Sitelink description 2 "
                    f"exceeds 35 characters"
                )

        return {
            "status":
                (
                    "READY_FOR_CREATION"
                    if not validation_errors
                    else
                    "VALIDATION_FAILED"
                ),

            "validation": {
                "passed":
                    len(
                        validation_errors
                    ) == 0,

                "errors":
                    validation_errors,
            },

            "summary":
                result.get(
                    "summary",
                    {}
                ),
        }

    except Exception as error:

        return {
            "status":
                "FAILED",

            "error":
                str(error),
        }
