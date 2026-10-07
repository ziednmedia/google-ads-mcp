import os
import secrets
import tempfile
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from google.ads.googleads.client import (
    GoogleAdsClient
)

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

# ============================================================
# END VALIDATE
# ============================================================
# ============================================================
# PREVIEW
# ============================================================
@router.post("/preview")
async def preview_search_campaign(
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

        data = (
            SearchCampaignService
            .read_excel(
                temp_path
            )
        )

        campaign = data.get(
            "campaign",
            {}
        )

        ad_groups = data.get(
            "ad_groups",
            []
        )

        ads = data.get(
            "ads",
            []
        )

        keywords = data.get(
            "keywords",
            []
        )

        sitelinks = data.get(
            "sitelinks",
            []
        )

        total_objects = (
            1
            + len(ad_groups)
            + len(ads)
            + len(keywords)
            + len(sitelinks)
        )

        return {

            "status":
                "READY_TO_CREATE",

            "automatic_action":
                False,

            "requires_human_confirmation":
                True,

            "campaign": {
                "campaign_name":
                    campaign.get(
                        "campaign_name"
                    ),
            "confirmation_required":
                True,
            "creation_plan": [
                {
                    "step": 1,
                    "action":
                    "Create Campaign Budget"
                },
                {
                    "step": 2,
                    "action":
                    "Create Campaign"
                },
                {
                    "step": 3,
                    "action":
                    "Create Campaign Criteria"
                },
                {
                    "step": 4,
                    "action":
                    "Create Ad Groups"
                },
                {
                    "step": 5,
                    "action":
                    "Create Keywords"
                },
                {
                    "step": 6,
                    "action":
                    "Create Responsive Search Ads"
                },
                {
                    "step": 7,
                    "action":
                    "Create Sitelinks"
                }
            ],

                "customer_id":
                    campaign.get(
                        "customer_id"
                    ),

                "objective":
                    campaign.get(
                        "objective"
                    ),

                "daily_budget":
                    campaign.get(
                        "daily_budget"
                    ),

                "language":
                    campaign.get(
                        "language"
                    ),

                "network":
                    campaign.get(
                        "network"
                    ),

                "locations":
                    campaign.get(
                        "locations",
                        []
                    ),
            },

            "operations": {

                "campaigns": 1,

                "ad_groups":
                    len(
                        ad_groups
                    ),

                "keywords":
                    len(
                        keywords
                    ),

                "ads":
                    len(
                        ads
                    ),

                "sitelinks":
                    len(
                        sitelinks
                    ),
            },

            "estimated_objects": {
                "total":
                    total_objects
            },

            "preview": {

                "ad_group_names": [
                    group.get(
                        "name"
                    )
                    for group
                    in ad_groups
                ],

                "keywords_sample":
                    keywords[:10],

                "ads_sample":
                    ads[:3],

                "sitelinks_sample":
                    sitelinks[:4],
            },

            "next_step":
                "Utiliser /campaigns/search/create pour créer la campagne dans Google Ads."
        }

    except Exception as error:

        return {
            "status":
                "FAILED",

            "error":
                str(error),
        }
# ============================================================
# END PREVIEW
# ============================================================
# ============================================================
# CREATE
# ============================================================


# ============================================================
# HELPERS
# ============================================================

def _normalize_customer_id(
    customer_id,
):
    normalized = str(
        customer_id or ""
    ).replace(
        "-",
        "",
    ).strip()

    if not normalized.isdigit():
        raise ValueError(
            "Customer ID invalide."
        )

    return normalized


def _normalize_date(
    value,
):
    if value is None:
        return None

    if isinstance(
        value,
        datetime,
    ):
        return value.date().isoformat()

    if isinstance(
        value,
        date,
    ):
        return value.isoformat()

    text = str(
        value
    ).strip()

    if not text:
        return None

    return text.split(
        " "
    )[0]


def _to_bool(
    value,
):
    if isinstance(
        value,
        bool,
    ):
        return value

    return str(
        value or ""
    ).strip().upper() in {
        "TRUE",
        "YES",
        "1",
    }


def _google_ads_errors(
    error,
):
    details = []

    for api_error in (
        error.failure.errors
    ):
        details.append(
            {
                "message":
                    api_error.message,

                "error_code":
                    str(
                        api_error.error_code
                    ),

                "field_path":
                    (
                        str(
                            api_error.location
                        )
                        if api_error.location
                        else None
                    ),
            }
        )

    return details


def _validate_creation_data(
    data,
):
    errors = []

    campaign = data.get(
        "campaign",
        {},
    )

    ad_groups = data.get(
        "ad_groups",
        [],
    )

    ads = data.get(
        "ads",
        [],
    )

    keywords = data.get(
        "keywords",
        [],
    )

    sitelinks = data.get(
        "sitelinks",
        [],
    ) or []

    if not campaign.get(
        "customer_id"
    ):
        errors.append(
            "Customer ID manquant."
        )

    if not campaign.get(
        "campaign_name"
    ):
        errors.append(
            "Nom de campagne manquant."
        )

    daily_budget = campaign.get(
        "daily_budget"
    )

    if (
        not isinstance(
            daily_budget,
            (
                int,
                float,
            ),
        )
        or daily_budget <= 0
    ):
        errors.append(
            "Le budget quotidien doit être supérieur à 0."
        )

    if not ad_groups:
        errors.append(
            "Au moins un groupe d'annonces est requis."
        )

    ad_group_names = set()

    for ad_group in ad_groups:
        name = str(
            ad_group.get(
                "name"
            )
            or ""
        ).strip()

        if not name:
            errors.append(
                "Un groupe d'annonces n'a pas de nom."
            )
            continue

        if name.casefold() in {
            item.casefold()
            for item in ad_group_names
        }:
            errors.append(
                f"Groupe d'annonces en double : {name}."
            )

        ad_group_names.add(
            name
        )

        if not ad_group.get(
            "final_url"
        ):
            errors.append(
                f"{name} : URL finale manquante."
            )

        path1 = str(
            ad_group.get(
                "path1"
            )
            or ""
        )

        path2 = str(
            ad_group.get(
                "path2"
            )
            or ""
        )

        if len(path1) > 15:
            errors.append(
                f"{name} : path1 dépasse 15 caractères."
            )

        if len(path2) > 15:
            errors.append(
                f"{name} : path2 dépasse 15 caractères."
            )

        if path2 and not path1:
            errors.append(
                f"{name} : path2 nécessite path1."
            )

    ads_by_group = {
        ad.get(
            "ad_group_name"
        ): ad
        for ad in ads
        if ad.get(
            "ad_group_name"
        )
    }

    for ad_group_name in ad_group_names:
        if ad_group_name not in ads_by_group:
            errors.append(
                f"{ad_group_name} : aucune annonce RSA."
            )

    for ad in ads:
        ad_group_name = ad.get(
            "ad_group_name"
        )

        headlines = (
            ad.get(
                "headlines"
            )
            or []
        )

        descriptions = (
            ad.get(
                "descriptions"
            )
            or []
        )

        if ad_group_name not in ad_group_names:
            errors.append(
                f"{ad_group_name} : groupe d'annonces introuvable."
            )

        if not (
            3 <= len(
                headlines
            ) <= 15
        ):
            errors.append(
                f"{ad_group_name} : entre 3 et 15 titres sont requis."
            )

        if not (
            2 <= len(
                descriptions
            ) <= 4
        ):
            errors.append(
                f"{ad_group_name} : entre 2 et 4 descriptions sont requises."
            )

        for position, headline in enumerate(
            headlines,
            start=1,
        ):
            if len(
                str(
                    headline
                )
            ) > 30:
                errors.append(
                    f"{ad_group_name} : titre {position} dépasse 30 caractères."
                )

        for position, description in enumerate(
            descriptions,
            start=1,
        ):
            if len(
                str(
                    description
                )
            ) > 90:
                errors.append(
                    f"{ad_group_name} : description {position} dépasse 90 caractères."
                )

        if not ad.get(
            "final_url"
        ):
            errors.append(
                f"{ad_group_name} : URL finale RSA manquante."
            )

    allowed_match_types = {
        "EXACT",
        "PHRASE",
        "BROAD",
    }

    for keyword in keywords:
        ad_group_name = keyword.get(
            "ad_group_name"
        )

        keyword_text = str(
            keyword.get(
                "keyword"
            )
            or ""
        ).strip()

        match_type = str(
            keyword.get(
                "match_type"
            )
            or ""
        ).strip().upper()

        if ad_group_name not in ad_group_names:
            errors.append(
                f"Mot-clé '{keyword_text}' : groupe d'annonces introuvable."
            )

        if not keyword_text:
            errors.append(
                "Un mot-clé est vide."
            )

        if (
            match_type
            not in allowed_match_types
        ):
            errors.append(
                f"Mot-clé '{keyword_text}' : type de correspondance invalide."
            )

    # Les sitelinks sont facultatifs.
    # Ils sont validés seulement lorsqu'ils existent.
    for sitelink in sitelinks:
        title = str(
            sitelink.get(
                "title"
            )
            or ""
        ).strip()

        description_1 = str(
            sitelink.get(
                "description_1"
            )
            or ""
        ).strip()

        description_2 = str(
            sitelink.get(
                "description_2"
            )
            or ""
        ).strip()

        if not title:
            errors.append(
                "Un sitelink présent dans Excel n'a aucun titre."
            )

        if len(title) > 25:
            errors.append(
                f"Sitelink '{title}' : titre supérieur à 25 caractères."
            )

        if len(
            description_1
        ) > 35:
            errors.append(
                f"Sitelink '{title}' : description 1 supérieure à 35 caractères."
            )

        if len(
            description_2
        ) > 35:
            errors.append(
                f"Sitelink '{title}' : description 2 supérieure à 35 caractères."
            )

        if not sitelink.get(
            "final_url"
        ):
            errors.append(
                f"Sitelink '{title}' : URL finale manquante."
            )

    return errors


def _language_ids(
    language,
):
    normalized = str(
        language or ""
    ).strip().casefold()

    language_map = {
        "french": [
            "1002"
        ],
        "français": [
            "1002"
        ],
        "francais": [
            "1002"
        ],
        "fr": [
            "1002"
        ],
        "english": [
            "1000"
        ],
        "anglais": [
            "1000"
        ],
        "en": [
            "1000"
        ],
        "both": [
            "1002",
            "1000",
        ],
        "bilingual": [
            "1002",
            "1000",
        ],
    }

    if normalized not in language_map:
        raise ValueError(
            f"Langue non prise en charge : {language}."
        )

    return language_map[
        normalized
    ]


def _resolve_location_ids(
    client,
    locations,
):
    if not locations:
        return []

    geo_service = client.get_service(
        "GeoTargetConstantService"
    )

    location_ids = []

    for location in locations:
        location_name = str(
            location
        ).strip()

        if not location_name:
            continue

        request = client.get_type(
            "SuggestGeoTargetConstantsRequest"
        )

        request.locale = "fr"
        request.country_code = "CA"
        request.location_names.names.append(
            location_name
        )

        response = (
            geo_service
            .suggest_geo_target_constants(
                request=request
            )
        )

        if not response.geo_target_constant_suggestions:
            raise ValueError(
                f"Localisation introuvable : {location_name}."
            )

        suggestion = (
            response
            .geo_target_constant_suggestions[
                0
            ]
        )

        location_ids.append(
            str(
                suggestion
                .geo_target_constant
                .resource_name
                .split("/")[-1]
            )
        )

    return location_ids


def _create_budget(
    client,
    customer_id,
    campaign_name,
    daily_budget,
):
    budget_service = client.get_service(
        "CampaignBudgetService"
    )

    operation = client.get_type(
        "CampaignBudgetOperation"
    )

    budget = operation.create

    budget.name = (
        f"{campaign_name} - Budget"
    )

    budget.amount_micros = int(
        float(
            daily_budget
        )
        * 1_000_000
    )

    budget.delivery_method = (
        client.enums
        .BudgetDeliveryMethodEnum
        .STANDARD
    )

    budget.explicitly_shared = False

    response = (
        budget_service
        .mutate_campaign_budgets(
            customer_id=customer_id,
            operations=[
                operation
            ],
        )
    )

    return (
        response
        .results[
            0
        ]
        .resource_name
    )


def _create_campaign(
    client,
    customer_id,
    campaign_data,
    budget_resource_name,
):
    campaign_service = client.get_service(
        "CampaignService"
    )

    operation = client.get_type(
        "CampaignOperation"
    )

    campaign = operation.create

    campaign.name = campaign_data[
        "campaign_name"
    ]
    #campaign.geo_target_type_setting.positive_geo_target_type = (
        #client.enums
        #.PositiveGeoTargetTypeEnum.PRESENCE
    #)
    #campaign.geo_target_type_setting.negative_geo_target_type = (
        #client.enums
        #.NegativeGeoTargetTypeEnum.PRESENCE
    #)
    campaign.contains_eu_political_advertising = (
        client.enums
        .EuPoliticalAdvertisingStatusEnum
        .DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    )

    campaign.advertising_channel_type = (
        client.enums
        .AdvertisingChannelTypeEnum
        .SEARCH
    )

    campaign.status = (
        client.enums
        .CampaignStatusEnum
        .PAUSED
    )

    campaign.campaign_budget = (
        budget_resource_name
    )

    network = str(
        campaign_data.get(
            "network"
        )
        or "SEARCH"
    ).upper()

    campaign.network_settings.target_google_search = True

    campaign.network_settings.target_search_network = (
        network
        == "SEARCH_PARTNERS"
    )

    campaign.network_settings.target_content_network = False
    campaign.network_settings.target_partner_search_network = False

    

    bidding_strategy = str(
        campaign_data.get(
            "bidding_strategy"
        )
        or ""
    ).upper()
       
    if (
        bidding_strategy
        == "MAXIMIZE_CONVERSIONS"
    ):
        pass
        campaign.maximize_conversions = (
            client.get_type(
                "MaximizeConversions"
            )
        )

    elif (
        bidding_strategy
        == "MAXIMIZE_CLICKS"
    ):
        campaign.maximize_clicks = (
            client.get_type(
                "MaximizeClicks"
            )
        )

    else:
        raise ValueError(
            "La première version de /create prend en charge "
            "MAXIMIZE_CONVERSIONS et MAXIMIZE_CLICKS."
        )

    

    start_date = _normalize_date(
        campaign_data.get(
            "start_date"
        )
    )

    end_date = _normalize_date(
        campaign_data.get(
            "end_date"
        )
    )

    #if start_date:
        #campaign.start_date = (
            #start_date.replace(
                #"-",
                #"",
            #)
        #)

    #if end_date:
        #campaign.end_date = (
            #end_date.replace(
                #"-",
                #"",
            #)
        #)
#----------------------------------------------------------------------------------------------------------------------------------------------------------
#return {
    #"campaign_fields": dir(campaign)
#}

    response = (
        campaign_service
        .mutate_campaigns(
            customer_id=customer_id,
            operations=[
                operation
            ],
        )
    )

    return (
        response
        .results[
            0
        ]
        .resource_name
    )


def _create_campaign_criteria(
    client,
    customer_id,
    campaign_resource_name,
    language_ids,
    location_ids,
):
    criterion_service = client.get_service(
        "CampaignCriterionService"
    )

    operations = []

    for language_id in language_ids:
        operation = client.get_type(
            "CampaignCriterionOperation"
        )

        criterion = operation.create
        criterion.campaign = campaign_resource_name
        criterion.language.language_constant = (
            f"languageConstants/{language_id}"
        )

        operations.append(
            operation
        )

    for location_id in location_ids:
        operation = client.get_type(
            "CampaignCriterionOperation"
        )

        criterion = operation.create
        criterion.campaign = campaign_resource_name
        criterion.location.geo_target_constant = (
            f"geoTargetConstants/{location_id}"
        )

        operations.append(
            operation
        )

    if not operations:
        return []

    response = (
        criterion_service
        .mutate_campaign_criteria(
            customer_id=customer_id,
            operations=operations,
        )
    )

    return [
        result.resource_name
        for result in response.results
    ]


def _create_ad_groups(
    client,
    customer_id,
    campaign_resource_name,
    ad_groups,
):
    ad_group_service = client.get_service(
        "AdGroupService"
    )

    operations = []

    for item in ad_groups:
        operation = client.get_type(
            "AdGroupOperation"
        )

        ad_group = operation.create

        ad_group.name = item[
            "name"
        ]

        ad_group.campaign = (
            campaign_resource_name
        )

        ad_group.status = (
            client.enums
            .AdGroupStatusEnum
            .ENABLED
        )

        ad_group.type_ = (
            client.enums
            .AdGroupTypeEnum
            .SEARCH_STANDARD
        )

        operations.append(
            operation
        )

    response = (
        ad_group_service
        .mutate_ad_groups(
            customer_id=customer_id,
            operations=operations,
        )
    )

    return {
        item["name"]:
            result.resource_name
        for item, result in zip(
            ad_groups,
            response.results,
        )
    }


def _create_keywords(
    client,
    customer_id,
    keywords,
    ad_group_resources,
):
    criterion_service = client.get_service(
        "AdGroupCriterionService"
    )

    operations = []

    for item in keywords:
        ad_group_name = item[
            "ad_group_name"
        ]

        operation = client.get_type(
            "AdGroupCriterionOperation"
        )

        criterion = operation.create

        criterion.ad_group = (
            ad_group_resources[
                ad_group_name
            ]
        )

        criterion.status = (
            client.enums
            .AdGroupCriterionStatusEnum
            .ENABLED
        )

        criterion.keyword.text = item[
            "keyword"
        ]

        match_type = str(
            item.get(
                "match_type"
            )
            or ""
        ).upper()

        criterion.keyword.match_type = (
            getattr(
                client.enums
                .KeywordMatchTypeEnum,
                match_type,
            )
        )

        criterion.negative = _to_bool(
            item.get(
                "negative"
            )
        )

        operations.append(
            operation
        )

    if not operations:
        return []

    response = (
        criterion_service
        .mutate_ad_group_criteria(
            customer_id=customer_id,
            operations=operations,
        )
    )

    return [
        result.resource_name
        for result in response.results
    ]


def _create_responsive_search_ads(
    client,
    customer_id,
    ads,
    ad_group_resources,
):
    ad_service = client.get_service(
        "AdGroupAdService"
    )

    operations = []

    for item in ads:
        operation = client.get_type(
            "AdGroupAdOperation"
        )

        ad_group_ad = operation.create

        ad_group_ad.ad_group = (
            ad_group_resources[
                item[
                    "ad_group_name"
                ]
            ]
        )

        ad_group_ad.status = (
            client.enums
            .AdGroupAdStatusEnum
            .ENABLED
        )

        ad_group_ad.ad.final_urls.append(
            item[
                "final_url"
            ]
        )

        if item.get(
            "path1"
        ):
            (
                ad_group_ad
                .ad
                .responsive_search_ad
                .path1
            ) = item[
                "path1"
            ]

        if item.get(
            "path2"
        ):
            (
                ad_group_ad
                .ad
                .responsive_search_ad
                .path2
            ) = item[
                "path2"
            ]

        for headline in item.get(
            "headlines",
            [],
        ):
            text_asset = client.get_type(
                "AdTextAsset"
            )

            text_asset.text = headline

            (
                ad_group_ad
                .ad
                .responsive_search_ad
                .headlines
                .append(
                   text_asset
                )
            )

        for description in item.get(
            "descriptions",
            [],
        ):
            text_asset = client.get_type(
                "AdTextAsset"
            )

            text_asset.text = description

            (
                ad_group_ad
                .ad
                .responsive_search_ad
                .descriptions
                .append(
                    text_asset
                )
            )

        operations.append(
            operation
        )

    response = (
        ad_service
        .mutate_ad_group_ads(
            customer_id=customer_id,
            operations=operations,
        )
    )

    return [
        result.resource_name
        for result in response.results
    ]


def _create_sitelinks(
    client,
    customer_id,
    sitelinks,
    ad_group_resources,
):
    # Les sitelinks sont facultatifs.
    if not sitelinks:
        return {
            "assets": [],
            "links": [],
        }

    asset_service = client.get_service(
        "AssetService"
    )

    asset_operations = []

    valid_sitelinks = []

    for item in sitelinks:
        title = str(
            item.get(
                "title"
            )
            or ""
        ).strip()

        final_url = str(
            item.get(
                "final_url"
            )
            or ""
        ).strip()

        if not title or not final_url:
            continue

        operation = client.get_type(
            "AssetOperation"
        )

        asset = operation.create

        asset.name = (
            f"Sitelink - {title}"
        )

        asset.sitelink_asset.link_text = title

        description_1 = str(
            item.get(
                "description_1"
            )
            or ""
        ).strip()

        description_2 = str(
            item.get(
                "description_2"
            )
            or ""
        ).strip()

        if description_1:
            asset.sitelink_asset.description1 = (
                description_1
            )

        if description_2:
            asset.sitelink_asset.description2 = (
                description_2
            )

        asset.final_urls.append(
            final_url
        )

        asset_operations.append(
            operation
        )

        valid_sitelinks.append(
            item
        )

    if not asset_operations:
        return {
            "assets": [],
            "links": [],
        }

    asset_response = (
        asset_service
        .mutate_assets(
            customer_id=customer_id,
            operations=asset_operations,
        )
    )

    asset_resources = [
        result.resource_name
        for result in asset_response.results
    ]

    ad_group_asset_service = (
        client.get_service(
            "AdGroupAssetService"
        )
    )

    link_operations = []

    for item, asset_resource in zip(
        valid_sitelinks,
        asset_resources,
    ):
        ad_group_name = item.get(
            "ad_group"
        )

        if (
            not ad_group_name
            or ad_group_name
            not in ad_group_resources
        ):
            continue

        operation = client.get_type(
            "AdGroupAssetOperation"
        )

        ad_group_asset = (
            operation.create
        )

        ad_group_asset.ad_group = (
            ad_group_resources[
                ad_group_name
            ]
        )

        ad_group_asset.asset = (
            asset_resource
        )

        ad_group_asset.field_type = (
            client.enums
            .AssetFieldTypeEnum
            .SITELINK
        )

        link_operations.append(
            operation
        )

    if not link_operations:
        return {
            "assets":
                asset_resources,

            "links":
                [],
        }

    link_response = (
        ad_group_asset_service
        .mutate_ad_group_assets(
            customer_id=customer_id,
            operations=link_operations,
        )
    )

    return {
        "assets":
            asset_resources,

        "links": [
            result.resource_name
            for result
            in link_response.results
        ],
    }


# ============================================================
# CREATE SEARCH CAMPAIGN
# ============================================================

@router.post("/create")
async def create_search_campaign(
    excel_file: UploadFile = File(...),
    confirmation_code: str = Form(...),
    validate_only: bool = Form(
        default=True
    ),
):
    temp_path = None

    try:
        expected_code = os.getenv(
            "CONFIRMATION_CODE"
        )

        if not expected_code:
            return {
                "status":
                    "FAILED",

                "automatic_action":
                    False,

                "error":
                    (
                        "La variable d'environnement "
                        "CONFIRMATION_CODE n'est pas configurée."
                    ),
            }

        if not confirmation_code:
            return {
                "status":
                    "CONFIRMATION_REQUIRED",

                "automatic_action":
                    False,

                "error":
                    "Le code de confirmation est requis.",
            }

        if not secrets.compare_digest(
            str(
                confirmation_code
            ),
            str(
                expected_code
            ),
        ):
            return {
                "status":
                    "CONFIRMATION_REQUIRED",

                "automatic_action":
                    False,

                "error":
                    "Code de confirmation incorrect.",
            }

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".xlsx",
        ) as temp_file:
            contents = await excel_file.read()

            if not contents:
                return {
                    "status":
                        "FAILED",

                    "automatic_action":
                        False,

                    "error":
                        "Le fichier Excel est vide.",
                }

            temp_file.write(
                contents
            )

            temp_path = (
                temp_file.name
            )

        data = (
            SearchCampaignService
            .read_excel(
                temp_path
            )
        )

        validation_errors = (
            _validate_creation_data(
                data
            )
        )

        if validation_errors:
            return {
                "status":
                    "VALIDATION_FAILED",

                "automatic_action":
                    False,

                "validation": {
                    "passed":
                        False,

                    "errors":
                        validation_errors,
                },

                "summary":
                    data.get(
                        "summary",
                        {},
                    ),
            }

        campaign_data = data[
            "campaign"
        ]

        ad_groups = data.get(
            "ad_groups",
            [],
        )

        keywords = data.get(
            "keywords",
            [],
        )

        ads = data.get(
            "ads",
            [],
        )

        # Les sitelinks sont optionnels.
        sitelinks = data.get(
            "sitelinks",
            [],
        ) or []

        allow_creation = os.getenv(
            "ALLOW_CAMPAIGN_CREATION",
            "false"
        ).lower() == "true"

        if not allow_creation:
            return {
                "status":"CREATION_DISABLED",
                "error":"La création réelle de campagnes est désactivée. "
            }

        if validate_only:
            return {
                "status":
                    "VALIDATED_ONLY",

                "automatic_action":
                    False,

                "created":
                    False,

                "confirmation_verified":
                    True,

                "message": (
                    "Les données sont valides. "
                    "Aucun objet Google Ads n'a été créé."
                ),

                "operations": {
                    "campaign_budgets":
                        1,

                    "campaigns":
                        1,

                    "ad_groups":
                        len(
                            ad_groups
                        ),

                    "keywords":
                        len(
                            keywords
                        ),

                    "ads":
                        len(
                            ads
                        ),

                    "sitelinks":
                        len(
                            sitelinks
                        ),
                },

                "next_step": (
                    "Relancer le même endpoint avec "
                    "validate_only=false pour créer "
                    "la campagne en pause."
                ),
            }

        customer_id = (
            _normalize_customer_id(
                campaign_data.get(
                    "customer_id"
                )
            )
        )

        

        config = {
            "developer_token":
                os.getenv(
                    "GOOGLE_ADS_DEVELOPER_TOKEN"
            ),

            "client_id":
                os.getenv(
                    "GOOGLE_ADS_CLIENT_ID"
            ),

            "client_secret":
                os.getenv(
                    "GOOGLE_ADS_CLIENT_SECRET"
            ),

            "refresh_token":
                os.getenv(
                    "GOOGLE_ADS_REFRESH_TOKEN"
            ),

            "login_customer_id":
                os.getenv(
                    "GOOGLE_ADS_LOGIN_CUSTOMER_ID"
            ),

            "use_proto_plus":
                True,
        }

        client = GoogleAdsClient.load_from_dict(
            config
        )

        language_ids = (
            _language_ids(
                campaign_data.get(
                    "language"
                )
            )
        )

        location_ids = (
            _resolve_location_ids(
                client=client,
                locations=campaign_data.get(
                    "locations",
                    [],
                ),
            )
        )

        creation_result = {
            "budget":
                None,

            "campaign":
                None,

            "campaign_criteria":
                [],

            "ad_groups":
                {},

            "keywords":
                [],

            "ads":
                [],

            "sitelinks": {
                "assets": [],
                "links": [],
            },
        }

        budget_resource_name = (
            _create_budget(
                client=client,
                customer_id=customer_id,
                campaign_name=campaign_data[
                    "campaign_name"
                ],
                daily_budget=campaign_data[
                    "daily_budget"
                ],
            )
        )

        creation_result[
            "budget"
        ] = budget_resource_name

        campaign_resource_name = (
            _create_campaign(
                client=client,
                customer_id=customer_id,
                campaign_data=campaign_data,
                budget_resource_name=(
                    budget_resource_name
                ),
            )
        )

        creation_result[
            "campaign"
        ] = campaign_resource_name

        creation_result[
            "campaign_criteria"
        ] = _create_campaign_criteria(
            client=client,
            customer_id=customer_id,
            campaign_resource_name=(
                campaign_resource_name
            ),
            language_ids=language_ids,
            location_ids=location_ids,
        )

        ad_group_resources = (
            _create_ad_groups(
                client=client,
                customer_id=customer_id,
                campaign_resource_name=(
                    campaign_resource_name
                ),
                ad_groups=ad_groups,
            )
        )

        creation_result[
            "ad_groups"
        ] = ad_group_resources

        creation_result[
            "keywords"
        ] = _create_keywords(
            client=client,
            customer_id=customer_id,
            keywords=keywords,
            ad_group_resources=(
                ad_group_resources
            ),
        )

        creation_result[
            "ads"
        ] = (
            _create_responsive_search_ads(
                client=client,
                customer_id=customer_id,
                ads=ads,
                ad_group_resources=(
                    ad_group_resources
                ),
            )
        )

        creation_result[
            "sitelinks"
        ] = _create_sitelinks(
            client=client,
            customer_id=customer_id,
            sitelinks=sitelinks,
            ad_group_resources=(
                ad_group_resources
            ),
        )

        return {
            "status":
                "CREATED",

            "automatic_action":
                True,

            "confirmation_verified":
                True,

            "customer_id":
                customer_id,

            "campaign_status":
                "PAUSED",

            "campaign_name":
                campaign_data[
                    "campaign_name"
                ],

            "created_resources":
                creation_result,

            "created_counts": {
                "campaign_budgets":
                    1,

                "campaigns":
                    1,

                "ad_groups":
                    len(
                        ad_group_resources
                    ),

                "keywords":
                    len(
                        creation_result[
                            "keywords"
                        ]
                    ),

                "ads":
                    len(
                        creation_result[
                            "ads"
                        ]
                    ),

                "sitelink_assets":
                    len(
                        creation_result[
                            "sitelinks"
                        ][
                            "assets"
                        ]
                    ),

                "sitelink_links":
                    len(
                        creation_result[
                            "sitelinks"
                        ][
                            "links"
                        ]
                    ),
            },

            "message": (
                "La campagne Search a été créée "
                "en pause dans Google Ads."
            ),
        }

    except GoogleAdsException as error:
        return {
            "status":
                "GOOGLE_ADS_API_FAILED",

            "automatic_action":
                True,

            "request_id":
                error.request_id,

            "errors":
                _google_ads_errors(
                    error
                ),

            "warning": (
                "La création est séquentielle. "
                "Certains objets peuvent avoir été créés "
                "avant l'erreur. Vérifier le compte Google Ads."
            ),
        }

    except Exception as error:
        return {
            "status":
                "FAILED",

            "automatic_action":
                False,

            "error":
                str(
                    error
                ),
        }

    finally:
        if (
            temp_path
            and os.path.exists(
                temp_path
            )
        ):
            os.remove(
                temp_path
            )
# ============================================================
# END CREATE
# ============================================================
