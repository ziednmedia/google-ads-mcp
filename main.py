import os
from typing import Any, Dict, List, Optional
from datetime import date
from fastapi import FastAPI, Query
from pydantic import BaseModel
from google.ads.googleads.client import GoogleAdsClient

        
class BudgetUpdateRequest(
        BaseModel
):
        customer_id: str
        campaign_id: str
        new_budget: float
        confirmation_code: str

class CampaignActionRequest(
    BaseModel
):
    customer_id: str
    campaign_id: str
    confirmation_code: str

class AdGroupActionRequest(BaseModel):
    customer_id: str
    campaign_id: str
    ad_group_id: str
    confirmation_code: str

class AddNegativeKeywordRequest(
    BaseModel
):
    customer_id: str
    campaign_id: str
    keyword: str
    match_type: str = "EXACT"
    level: str = "CAMPAIGN"
    ad_group_id: Optional[str] = None
    confirmation_code: str

class RemoveNegativeKeywordRequest(
    BaseModel
):
    customer_id: str
    campaign_id: str
    level: str
    resource_name: str
    confirmation_code: str

class AddKeywordRequest(
    BaseModel
):
    customer_id: str
    campaign_id: str
    ad_group_id: str
    keyword: str
    match_type: str = "EXACT"
    confirmation_code: str


app = FastAPI(
    title="Google Ads Optimization API",
    version="1.0.0",
    description=(
        "API Google Ads en lecture seule pour analyser les campagnes "
        "et identifier des opportunités d'optimisation."
    ),
    openapi_version="3.0.2",
)

# ============================================================
# GOOGLE ADS DATE FILTERS
# ============================================================

VALID_PERIODS = {
    "TODAY",
    "YESTERDAY",
    "LAST_7_DAYS",
    "LAST_14_DAYS",
    "LAST_30_DAYS",
    "LAST_BUSINESS_WEEK",
    "THIS_MONTH",
    "LAST_MONTH",
    "THIS_WEEK_SUN_TODAY",
    "THIS_WEEK_MON_TODAY",
    "LAST_WEEK_SUN_SAT",
    "LAST_WEEK_MON_SUN",
}


def validate_iso_date(
    value: str,
    field_name: str
) -> str:
    try:
        parsed_date = date.fromisoformat(
            value
        )

        return parsed_date.isoformat()

    except ValueError as error:
        raise ValueError(
            f"{field_name} doit respecter "
            f"le format YYYY-MM-DD."
        ) from error


def build_date_filter(
    period: str = "LAST_30_DAYS",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, str]:

    period = (
        period
        .strip()
        .upper()
    )

    # Les dates personnalisées doivent être fournies ensemble.
    if (
        start_date is not None
        or end_date is not None
    ):
        if not start_date or not end_date:
            raise ValueError(
                "start_date et end_date doivent "
                "être fournis ensemble."
            )

        normalized_start_date = (
            validate_iso_date(
                start_date,
                "start_date"
            )
        )

        normalized_end_date = (
            validate_iso_date(
                end_date,
                "end_date"
            )
        )

        if (
            normalized_start_date
            > normalized_end_date
        ):
            raise ValueError(
                "start_date ne peut pas être "
                "postérieure à end_date."
            )

        return {
            "filter": (
                "segments.date BETWEEN "
                f"'{normalized_start_date}' "
                "AND "
                f"'{normalized_end_date}'"
            ),
            "mode": "CUSTOM_DATE_RANGE",
            "period": "CUSTOM",
            "start_date": (
                normalized_start_date
            ),
            "end_date": (
                normalized_end_date
            ),
        }

    if period not in VALID_PERIODS:
        valid_values = ", ".join(
            sorted(VALID_PERIODS)
        )

        raise ValueError(
            f"Période invalide : {period}. "
            f"Valeurs acceptées : "
            f"{valid_values}. "
            f"Pour une période personnalisée, "
            f"utiliser start_date et end_date."
        )

    return {
        "filter": (
            f"segments.date DURING {period}"
        ),
        "mode": "PREDEFINED_PERIOD",
        "period": period,
        "start_date": None,
        "end_date": None,
    }

# ============================================================
# CONFIGURATION GOOGLE ADS
# ============================================================

def normalize_keyword_text(
    keyword: str
) -> str:
    return (
        keyword
        .strip()
        .casefold()
    )

def get_google_ads_client() -> GoogleAdsClient:
    config = {
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        "use_proto_plus": True,
    }

    missing = [
        key
        for key, value in config.items()
        if key != "use_proto_plus" and not value
    ]

    if missing:
        raise ValueError(
            "Variables Google Ads manquantes : " + ", ".join(missing)
        )

    return GoogleAdsClient.load_from_dict(config)


def normalize_customer_id(
    customer_id: str
) -> str:

    if not customer_id:
        raise ValueError(
            "customer_id est obligatoire."
        )

    return customer_id.replace(
        "-",
        ""
    ).strip()


def execute_query(
    client: GoogleAdsClient,
    customer_id: str,
    query: str,
):
    google_ads_service = client.get_service(
        "GoogleAdsService"
    )

    response = google_ads_service.search(
        customer_id=customer_id,
        query=query,
    )

    return list(response)


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def enum_name(value: Any) -> str:
    try:
        return value.name
    except AttributeError:
        return str(value)


def add_opportunity(
    opportunities: List[Dict[str, Any]],
    priority: str,
    category: str,
    title: str,
    observation: str,
    recommendation: str,
    evidence: Optional[Dict[str, Any]] = None,
) -> None:
    opportunities.append(
        {
            "priority": priority,
            "category": category,
            "title": title,
            "observation": observation,
            "recommendation": recommendation,
            "evidence": evidence or {},
            "automatic_action": False,
            "requires_human_confirmation": True,
            "status": "RECOMMENDATION_ONLY",
        }
    )


def priority_order(priority: str) -> int:
    priorities = {
        "CRITICAL": 0,
        "HIGH": 1,
        "MEDIUM": 2,
        "LOW": 3,
        "INFO": 4,
    }

    return priorities.get(priority, 99)


# ============================================================
# ROUTES DE BASE
# ============================================================

@app.get("/")
def root():
    return {
        "name": "Google Ads Optimization API",
        "status": "running",
        "mode": "READ_ONLY",
        "automatic_actions": False,
    }


@app.get("/config")
def config():
    return {
        "customer_id": os.getenv("GOOGLE_ADS_CUSTOMER_ID"),
        "login_customer_id": os.getenv(
            "GOOGLE_ADS_LOGIN_CUSTOMER_ID"
        ),
        "client_id_exists": bool(
            os.getenv("GOOGLE_ADS_CLIENT_ID")
        ),
        "client_secret_exists": bool(
            os.getenv("GOOGLE_ADS_CLIENT_SECRET")
        ),
        "refresh_token_exists": bool(
            os.getenv("GOOGLE_ADS_REFRESH_TOKEN")
        ),
    }
 # ----------------------------------------------------     ---------------------------------------------------  --------------------------------------------------- ---------------------------------------------------
 
 # ----------------------------------------------------
 # BUDGET UPDATE
 # ----------------------------------------------------

@app.post("/update-budget")
def update_budget(
    request: BudgetUpdateRequest
):
    try:

        customer_id = normalize_customer_id(
            request.customer_id
        )
            
        expected_code = os.getenv(
            "CONFIRMATION_CODE"
        )

        if (
            request.confirmation_code
            != expected_code
        ):
            return {
                "status": "FAILED",
                "error": "Confirmation code invalid"
            }

        client = get_google_ads_client()

        google_ads_service = client.get_service(
            "GoogleAdsService"
        )

        campaign_budget_service = client.get_service(
            "CampaignBudgetService"
        )

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.campaign_budget,
                campaign_budget.amount_micros
            FROM campaign
            WHERE campaign.id = {request.campaign_id}
        """

        response = google_ads_service.search(
            customer_id=customer_id,
            query=query
        )

        row = next(iter(response), None)

        if not row:
            return {
                "error": "Campaign not found"
            }

        current_budget = (
            row.campaign_budget.amount_micros
            / 1000000
        )

        budget_resource_name = (
            row.campaign.campaign_budget
        )

        operation = client.get_type(
            "CampaignBudgetOperation"
        )

        operation.update.resource_name = (
            budget_resource_name
        )

        operation.update.amount_micros = int(
            request.new_budget * 1000000
        )

        operation.update_mask.paths.append(
            "amount_micros"
        )

        result = (
            campaign_budget_service
            .mutate_campaign_budgets(
                customer_id=customer_id,
                operations=[operation]
            )
        )

        return {
            "status": "SUCCESS",
            "campaign_name":
                row.campaign.name,
            "old_budget":
                current_budget,
            "new_budget":
                request.new_budget,
            "resource_name":
                result.results[0]
                .resource_name
        }

    except Exception as error:

        return {
            "status": "FAILED",
            "error": str(error)
        }
# ============================================================
# AD GROUPS
# ============================================================

@app.get("/ad-groups")
def ad_groups(
    customer_id: str = Query(
        ...,
        description="ID du compte Google Ads",
    ),
    campaign_id: str = Query(
        ...,
        description="ID de la campagne",
    ),
    period: str = Query(
        default="LAST_30_DAYS",
    ),
    start_date: Optional[str] = Query(
        default=None,
    ),
    end_date: Optional[str] = Query(
        default=None,
    ),
):
    try:

        customer_id = normalize_customer_id(
            customer_id
        )

        campaign_id = (
            campaign_id
            .replace("-", "")
            .strip()
        )

        date_configuration = (
            build_date_filter(
                period=period,
                start_date=start_date,
                end_date=end_date,
            )
        )

        date_filter = (
            date_configuration["filter"]
        )

        date_range = {
            "mode": (
                date_configuration["mode"]
            ),
            "period": (
                date_configuration["period"]
            ),
            "start_date": (
                date_configuration["start_date"]
            ),
            "end_date": (
                date_configuration["end_date"]
            ),
        }

        client = get_google_ads_client()

        query = f"""
            SELECT
                campaign.id,
                campaign.name,

                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.type,

                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.average_cpc,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.conversions_from_interactions_rate

            FROM ad_group

            WHERE campaign.id = {campaign_id}
              AND {date_filter}

            ORDER BY metrics.cost_micros DESC
        """

        response = execute_query(
            client,
            customer_id,
            query,
        )

        results = []

        campaign_name = ""

        for row in response:

            campaign_name = (
                row.campaign.name
            )

            cost = (
                row.metrics.cost_micros
                / 1_000_000
            )

            conversions = safe_float(
                row.metrics.conversions
            )

            conversion_value = safe_float(
                row.metrics.conversions_value
            )

            average_cpc = (
                row.metrics.average_cpc
                / 1_000_000
            )

            ctr = (
                safe_float(
                    row.metrics.ctr
                )
                * 100
            )

            conversion_rate = (
                safe_float(
                    row.metrics
                    .conversions_from_interactions_rate
                )
                * 100
            )

            cpa = (
                round(
                    cost / conversions,
                    2,
                )
                if conversions > 0
                else None
            )

            roas = (
                round(
                    conversion_value / cost,
                    2,
                )
                if cost > 0
                else None
            )

            results.append(
                {
                    "ad_group_id": str(
                        row.ad_group.id
                    ),

                    "ad_group_name": (
                        row.ad_group.name
                    ),

                    "status": enum_name(
                        row.ad_group.status
                    ),

                    "type": enum_name(
                        row.ad_group.type
                    ),

                    "impressions": (
                        row.metrics.impressions
                    ),

                    "clicks": (
                        row.metrics.clicks
                    ),

                    "ctr_percent": round(
                        ctr,
                        2,
                    ),

                    "average_cpc": round(
                        average_cpc,
                        2,
                    ),

                    "cost": round(
                        cost,
                        2,
                    ),

                    "conversions": round(
                        conversions,
                        2,
                    ),

                    "conversion_rate_percent": round(
                        conversion_rate,
                        2,
                    ),

                    "conversion_value": round(
                        conversion_value,
                        2,
                    ),

                    "cpa": cpa,

                    "roas": roas,
                }
            )

        total_cost = round(
            sum(
                item["cost"]
                for item in results
            ),
            2,
        )

        total_conversions = round(
            sum(
                item["conversions"]
                for item in results
            ),
            2,
        )

        total_conversion_value = round(
            sum(
                item["conversion_value"]
                for item in results
            ),
            2,
        )

        account_roas = (
            round(
                total_conversion_value
                / total_cost,
                2,
            )
            if total_cost > 0
            else None
        )

        account_cpa = (
            round(
                total_cost
                / total_conversions,
                2,
            )
            if total_conversions > 0
            else None
        )

        return {
            "status": "SUCCESS",

            "customer_id": customer_id,

            "campaign_id": campaign_id,

            "campaign_name": campaign_name,

            "date_range": date_range,

            "summary": {
                "total_ad_groups": len(
                    results
                ),

                "total_cost": total_cost,

                "total_conversions": (
                    total_conversions
                ),

                "total_conversion_value": (
                    total_conversion_value
                ),

                "account_cpa": (
                    account_cpa
                ),

                "account_roas": (
                    account_roas
                ),
            },

            "ad_groups": results,
        }

    except ValueError as error:

        return {
            "status": "FAILED",
            "error": str(error),
        }

    except Exception as error:

        return {
            "status": "FAILED",
            "error": str(error),
        }
# ============================================================
# TOP AD GROUPS
# ============================================================

@app.get("/top-ad-groups")
def top_ad_groups(
    customer_id: str = Query(
        ...,
        description="ID du compte Google Ads",
    ),
    campaign_id: str = Query(
        ...,
        description="ID de la campagne",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    ranking_by: str = Query(
        default="ROAS",
        description=(
            "ROAS | CPA | CONVERSIONS | "
            "CONVERSION_VALUE | CTR | "
            "CLICKS | COST | IMPRESSIONS | "
            "CONVERSION_RATE | AVG_CPC"
        ),
    ),
    period: str = Query(
        default="LAST_30_DAYS",
    ),
    start_date: Optional[str] = Query(
        default=None,
    ),
    end_date: Optional[str] = Query(
        default=None,
    ),
):
    try:

        ranking_by = (
            ranking_by.upper().strip()
        )

        valid_metrics = {
            "ROAS",
            "CPA",
            "CONVERSIONS",
            "CONVERSION_VALUE",
            "CTR",
            "CLICKS",
            "COST",
            "IMPRESSIONS",
            "CONVERSION_RATE",
            "AVG_CPC",
        }

        if ranking_by not in valid_metrics:

            return {
                "status": "FAILED",
                "error": (
                    f"ranking_by invalide. "
                    f"Valeurs acceptées : "
                    f"{sorted(valid_metrics)}"
                ),
            }

        performance = ad_groups(
            customer_id=customer_id,
            campaign_id=campaign_id,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )

        if (
            not isinstance(
                performance,
                dict,
            )
            or performance.get("status")
            != "SUCCESS"
        ):
            return performance

        ad_groups_data = (
            performance.get(
                "ad_groups",
                [],
            )
        )

        metric_field = {
            "ROAS": "roas",
            "CPA": "cpa",
            "CONVERSIONS": (
                "conversions"
            ),
            "CONVERSION_VALUE": (
                "conversion_value"
            ),
            "CTR": (
                "ctr_percent"
            ),
            "CLICKS": (
                "clicks"
            ),
            "COST": (
                "cost"
            ),
            "IMPRESSIONS": (
                "impressions"
            ),
            "CONVERSION_RATE": (
                "conversion_rate_percent"
            ),
            "AVG_CPC": (
                "average_cpc"
            ),
        }

        metric_name = (
            metric_field[
                ranking_by
            ]
        )

        ranked_ad_groups = [
            item
            for item in ad_groups_data
            if item.get(
                metric_name
            )
            is not None
        ]

        reverse_sort = (
            ranking_by != "CPA"
        )

        ranked_ad_groups.sort(
            key=lambda item:
                item[
                    metric_name
                ],
            reverse=reverse_sort,
        )

        return {
            "status": "SUCCESS",

            "customer_id":
                customer_id,

            "campaign_id":
                campaign_id,

            "campaign_name":
                performance.get(
                    "campaign_name"
                ),

            "date_range":
                performance.get(
                    "date_range"
                ),

            "summary": {

                "total_ad_groups":
                    len(
                        ad_groups_data
                    ),

                "ranked_ad_groups":
                    len(
                        ranked_ad_groups
                    ),

                "limit":
                    limit,

                "ranking_by":
                    ranking_by,
            },

            "top_ad_groups":
                ranked_ad_groups[
                    :limit
                ],
        }

    except ValueError as error:

        return {
            "status": "FAILED",
            "error": str(error),
        }

    except Exception as error:

        return {
            "status": "FAILED",
            "error": str(error),
        }
# ----------------------------------------------------
# PAUSE AD GROUPE
# ----------------------------------------------------
@app.post("/pause-ad-group")
def pause_ad_group(
    request: AdGroupActionRequest
):
    try:
        customer_id = normalize_customer_id(
            request.customer_id
        )

        campaign_id = (
            request.campaign_id
            .replace("-", "")
            .strip()
        )

        ad_group_id = (
            request.ad_group_id
            .replace("-", "")
            .strip()
        )

        expected_code = os.getenv(
            "CONFIRMATION_CODE"
        )

        if not expected_code:
            return {
                "status": "FAILED",
                "error": (
                    "CONFIRMATION_CODE is not configured"
                )
            }

        if (
            request.confirmation_code
            != expected_code
        ):
            return {
                "status": "FAILED",
                "error": (
                    "Confirmation code invalid"
                )
            }

        client = get_google_ads_client()

        google_ads_service = (
            client.get_service(
                "GoogleAdsService"
            )
        )

        ad_group_service = client.get_service(
            "AdGroupService"
        )

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.resource_name
            FROM ad_group
            WHERE campaign.id = {campaign_id}
              AND ad_group.id = {ad_group_id}
        """

        response = google_ads_service.search(
            customer_id=customer_id,
            query=query
        )

        row = next(iter(response), None)

        if not row:
            return {
                "status": "FAILED",
                "error": (
                    "Ad group not found in this campaign"
                )
            }

        previous_status = enum_name(
            row.ad_group.status
        )

        if previous_status == "PAUSED":
            return {
                "status": "NO_CHANGE",
                "campaign_id": campaign_id,
                "ad_group_id": ad_group_id,
                "ad_group_name": (
                    row.ad_group.name
                ),
                "previous_status": (
                    previous_status
                ),
                "new_status": "PAUSED",
                "message": (
                    "Ad group is already paused"
                )
            }

        operation = client.get_type(
            "AdGroupOperation"
        )

        operation.update.resource_name = (
            row.ad_group.resource_name
        )

        operation.update.status = (
            client.enums
            .AdGroupStatusEnum
            .PAUSED
        )

        operation.update_mask.paths.append(
            "status"
        )

        result = (
            ad_group_service
            .mutate_ad_groups(
                customer_id=customer_id,
                operations=[operation]
            )
        )

        return {
            "status": "SUCCESS",
            "campaign_id": campaign_id,
            "campaign_name": (
                row.campaign.name
            ),
            "ad_group_id": ad_group_id,
            "ad_group_name": (
                row.ad_group.name
            ),
            "previous_status": previous_status,
            "new_status": "PAUSED",
            "resource_name": (
                result.results[0]
                .resource_name
            )
        }

    except Exception as error:
        return {
            "status": "FAILED",
            "error": str(error)
        }

# ----------------------------------------------------
# ENABLE AD GROUPE
# ----------------------------------------------------
@app.post("/enable-ad-group")
def enable_ad_group(
    request: AdGroupActionRequest
):
    try:
        customer_id = normalize_customer_id(
            request.customer_id
        )

        campaign_id = (
            request.campaign_id
            .replace("-", "")
            .strip()
        )

        ad_group_id = (
            request.ad_group_id
            .replace("-", "")
            .strip()
        )

        expected_code = os.getenv(
            "CONFIRMATION_CODE"
        )

        if not expected_code:
            return {
                "status": "FAILED",
                "error": (
                    "CONFIRMATION_CODE is not configured"
                )
            }

        if (
            request.confirmation_code
            != expected_code
        ):
            return {
                "status": "FAILED",
                "error": (
                    "Confirmation code invalid"
                )
            }

        client = get_google_ads_client()

        google_ads_service = (
            client.get_service(
                "GoogleAdsService"
            )
        )

        ad_group_service = client.get_service(
            "AdGroupService"
        )

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.resource_name
            FROM ad_group
            WHERE campaign.id = {campaign_id}
              AND ad_group.id = {ad_group_id}
        """

        response = google_ads_service.search(
            customer_id=customer_id,
            query=query
        )

        row = next(iter(response), None)

        if not row:
            return {
                "status": "FAILED",
                "error": (
                    "Ad group not found in this campaign"
                )
            }

        campaign_status = enum_name(
            row.campaign.status
        )

        previous_status = enum_name(
            row.ad_group.status
        )

        if campaign_status != "ENABLED":
            return {
                "status": "FAILED",
                "error": (
                    "The parent campaign must be "
                    "enabled before enabling this "
                    "ad group"
                ),
                "campaign_status": (
                    campaign_status
                )
            }

        if previous_status == "ENABLED":
            return {
                "status": "NO_CHANGE",
                "ad_group_id": ad_group_id,
                "ad_group_name": (
                    row.ad_group.name
                ),
                "previous_status": (
                    previous_status
                ),
                "new_status": "ENABLED",
                "message": (
                    "Ad group is already enabled"
                )
            }

        operation = client.get_type(
            "AdGroupOperation"
        )

        operation.update.resource_name = (
            row.ad_group.resource_name
        )

        operation.update.status = (
            client.enums
            .AdGroupStatusEnum
            .ENABLED
        )

        operation.update_mask.paths.append(
            "status"
        )

        result = (
            ad_group_service
            .mutate_ad_groups(
                customer_id=customer_id,
                operations=[operation]
            )
        )

        return {
            "status": "SUCCESS",
            "campaign_id": campaign_id,
            "campaign_name": (
                row.campaign.name
            ),
            "ad_group_id": ad_group_id,
            "ad_group_name": (
                row.ad_group.name
            ),
            "previous_status": previous_status,
            "new_status": "ENABLED",
            "resource_name": (
                result.results[0]
                .resource_name
            )
        }

    except Exception as error:
        return {
            "status": "FAILED",
            "error": str(error)
        }
# ----------------------------------------------------
# ENABLE CAMPAGNE
# ----------------------------------------------------
@app.post("/enable-campaign")
def enable_campaign(
    request: CampaignActionRequest
):
    try:

        customer_id = normalize_customer_id(
            request.customer_id
        )

        expected_code = os.getenv(
            "CONFIRMATION_CODE"
        )

        if not expected_code:
            return {
                "status": "FAILED",
                "error":
                    "CONFIRMATION_CODE is not configured"
            }

        if (
            request.confirmation_code
            != expected_code
        ):
            return {
                "status": "FAILED",
                "error":
                    "Confirmation code invalid"
            }

        client = get_google_ads_client()

        google_ads_service = client.get_service(
            "GoogleAdsService"
        )

        campaign_service = client.get_service(
            "CampaignService"
        )

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.resource_name
            FROM campaign
            WHERE campaign.id = {request.campaign_id}
        """

        response = google_ads_service.search(
            customer_id=customer_id,
            query=query
        )

        row = next(iter(response), None)

        if not row:
            return {
                "status": "FAILED",
                "error":
                    "Campaign not found"
            }

        previous_status = enum_name(
            row.campaign.status
        )

        if previous_status == "ENABLED":
            return {
                "status": "NO_CHANGE",
                "campaign_id":
                    str(row.campaign.id),
                "campaign_name":
                    row.campaign.name,
                "previous_status":
                    previous_status,
                "new_status":
                    "ENABLED",
                "message":
                    "Campaign is already enabled"
            }

        operation = client.get_type(
            "CampaignOperation"
        )

        operation.update.resource_name = (
            row.campaign.resource_name
        )

        operation.update.status = (
            client.enums
            .CampaignStatusEnum
            .ENABLED
        )

        operation.update_mask.paths.append(
            "status"
        )

        result = campaign_service.mutate_campaigns(
            customer_id=customer_id,
            operations=[operation]
        )

        return {
            "status": "SUCCESS",
            "campaign_id":
                str(row.campaign.id),
            "campaign_name":
                row.campaign.name,
            "previous_status":
                previous_status,
            "new_status":
                "ENABLED",
            "resource_name":
                result.results[0]
                .resource_name
        }

    except Exception as error:

        return {
            "status": "FAILED",
            "error": str(error)
        }
# ----------------------------------------------------
# PAUSE CAMPAGNE
# ----------------------------------------------------
@app.post("/pause-campaign")
def pause_campaign(
    request: CampaignActionRequest
):
    try:

        customer_id = normalize_customer_id(
            request.customer_id
        )

        expected_code = os.getenv(
            "CONFIRMATION_CODE"
        )

        if (
            request.confirmation_code
            != expected_code
        ):
            return {
                "status": "FAILED",
                "error": "Confirmation code invalid"
            }

        client = get_google_ads_client()

        google_ads_service = client.get_service(
            "GoogleAdsService"
        )

        campaign_service = client.get_service(
            "CampaignService"
        )

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status
            FROM campaign
            WHERE campaign.id = {request.campaign_id}
        """

        response = google_ads_service.search(
            customer_id=customer_id,
            query=query
        )

        row = next(iter(response), None)

        if not row:
            return {
                "status": "FAILED",
                "error": "Campaign not found"
            }

        operation = client.get_type(
            "CampaignOperation"
        )

        operation.update.resource_name = (
            row.campaign.resource_name
        )

        operation.update.status = (
            client.enums.CampaignStatusEnum.PAUSED
        )

        operation.update_mask.paths.append(
            "status"
        )

        result = campaign_service.mutate_campaigns(
            customer_id=customer_id,
            operations=[operation]
        )

        return {
            "status": "SUCCESS",
            "campaign_id": str(row.campaign.id),
            "campaign_name": row.campaign.name,
            "new_status": "PAUSED",
            "resource_name": (
                result.results[0].resource_name
            )
        }

    except Exception as error:

        return {
            "status": "FAILED",
            "error": str(error)
        }
# ----------------------------------------------------
# CAMPAIGN HEALTH
# ----------------------------------------------------

@app.get("/campaign-health")
def campaign_health(
    customer_id: str = Query(
        ...,
        description="ID du compte Google Ads",
    ),
    campaign_id: str = Query(
        ...,
        description="ID de la campagne Google Ads",
    ),
    period: str = Query(
        default="LAST_30_DAYS",
        description=(
            "Période Google Ads prédéfinie."
        ),
    ),
    start_date: Optional[str] = Query(
        default=None,
        description=(
            "Date de début personnalisée "
            "au format YYYY-MM-DD"
        ),
    ),
    end_date: Optional[str] = Query(
        default=None,
        description=(
            "Date de fin personnalisée "
            "au format YYYY-MM-DD"
        ),
    ),
):
    try:

        customer_id = normalize_customer_id(
            customer_id
        )

        campaign_id = (
            campaign_id
            .replace("-", "")
            .strip()
        )

        if not campaign_id.isdigit():
            return {
                "status": "FAILED",
                "error": (
                    "campaign_id doit contenir "
                    "uniquement des chiffres."
                ),
            }

        date_configuration = (
            build_date_filter(
                period=period,
                start_date=start_date,
                end_date=end_date,
            )
        )

        date_filter = (
            date_configuration["filter"]
        )

        client = get_google_ads_client()

        google_ads_service = (
            client.get_service(
                "GoogleAdsService"
            )
        )

        # ----------------------------------------------------
        # CAMPAGNE
        # ----------------------------------------------------

        campaign_query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign_budget.amount_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM campaign
            WHERE campaign.id = {campaign_id}
              AND {date_filter}
        """

        campaign_response = (
            google_ads_service.search(
                customer_id=customer_id,
                query=campaign_query,
            )
        )

        campaign_row = next(
            iter(campaign_response),
            None,
        )

        if not campaign_row:
            return {
                "status": "FAILED",
                "error": "Campaign not found",
            }

        cost = (
            campaign_row.metrics.cost_micros
            / 1_000_000
        )

        conversions = safe_float(
            campaign_row.metrics.conversions
        )

        conversion_value = safe_float(
            campaign_row.metrics.conversions_value
        )

        ctr = (
            safe_float(
                campaign_row.metrics.ctr
            )
            * 100
        )

        cpa = (
            cost / conversions
            if conversions > 0
            else None
        )

        roas = (
            conversion_value / cost
            if cost > 0
            else None
        )

        # ----------------------------------------------------
        # GROUPES D'ANNONCES
        # ----------------------------------------------------

        ad_group_query = f"""
            SELECT
                ad_group.id,
                ad_group.status
            FROM ad_group
            WHERE campaign.id = {campaign_id}
        """

        ad_group_response = (
            google_ads_service.search(
                customer_id=customer_id,
                query=ad_group_query,
            )
        )

        total_ad_groups = 0
        enabled_ad_groups = 0
        paused_ad_groups = 0

        for row in ad_group_response:

            total_ad_groups += 1

            status = enum_name(
                row.ad_group.status
            )

            if status == "ENABLED":
                enabled_ad_groups += 1

            elif status == "PAUSED":
                paused_ad_groups += 1

        # ----------------------------------------------------
        # HEALTH V2
        # ----------------------------------------------------

        strengths = []
        warnings = []
        recommendations = []

        # ROAS

        if roas is not None:

            if roas >= 10:

                strengths.append(
                    f"Excellent ROAS ({round(roas,2)})"
                )

            elif roas < 2:

                warnings.append(
                    f"ROAS faible ({round(roas,2)})"
                )

                recommendations.append(
                    "Réviser les mots-clés, annonces et pages de destination."
                )

        # CTR

        if ctr >= 10:

            strengths.append(
                f"CTR élevé ({round(ctr,2)}%)"
            )

        elif ctr < 2:

            warnings.append(
                f"CTR faible ({round(ctr,2)}%)"
            )

            recommendations.append(
                "Tester de nouvelles annonces et améliorer la pertinence des mots-clés."
            )

        # CONVERSIONS

        if conversions > 0:

            strengths.append(
                (
                    f"{round(conversions,2)} "
                    f"conversions sur la période analysée"
                )
            )

        if conversions == 0 and cost > 50:

            warnings.append(
                "Dépenses importantes sans conversion."
            )

            recommendations.append(
                "Analyser les termes de recherche et les pages d'atterrissage."
            )

        # GROUPES D'ANNONCES

        if paused_ad_groups > 0:

            warnings.append(
                f"{paused_ad_groups} groupe(s) d'annonces sont en pause."
            )

            recommendations.append(
                "Valider si les groupes en pause doivent être réactivés."
            )

        if (
            total_ad_groups > 0
            and enabled_ad_groups
            == total_ad_groups
        ):

            strengths.append(
                "Tous les groupes d'annonces sont actifs."
            )

        # SCORE

        health_score = 100

        if ctr < 2:
            health_score -= 20

        if conversions == 0 and cost > 50:
            health_score -= 30

        if roas is not None:

            if roas < 1:
                health_score -= 30

            elif roas < 2:
                health_score -= 15

        if paused_ad_groups > 0:
            health_score -= 5

        health_score = max(
            0,
            min(
                100,
                round(health_score),
            ),
        )

        if health_score >= 90:
            health_status = "GOOD"

        elif health_score >= 70:
            health_status = "WARNING"

        else:
            health_status = "CRITICAL"

        return {

            "status": "SUCCESS",

            "customer_id": customer_id,

            "campaign_id": str(
                campaign_row.campaign.id
            ),

            "campaign_name": (
                campaign_row.campaign.name
            ),

            "campaign_status": enum_name(
                campaign_row.campaign.status
            ),

            "campaign_type": enum_name(
                campaign_row
                .campaign
                .advertising_channel_type
            ),

            "date_range": {
                "mode": (
                    date_configuration["mode"]
                ),
                "period": (
                    date_configuration["period"]
                ),
                "start_date": (
                    date_configuration["start_date"]
                ),
                "end_date": (
                    date_configuration["end_date"]
                ),
            },

            "budget": round(
                campaign_row
                .campaign_budget
                .amount_micros
                / 1_000_000,
                2,
            ),

            "performance": {

                "impressions":
                    campaign_row.metrics.impressions,

                "clicks":
                    campaign_row.metrics.clicks,

                "ctr_percent":
                    round(ctr, 2),

                "cost":
                    round(cost, 2),

                "conversions":
                    round(conversions, 2),

                "conversion_value":
                    round(
                        conversion_value,
                        2,
                    ),

                "cpa":
                    round(cpa, 2)
                    if cpa is not None
                    else None,

                "roas":
                    round(roas, 2)
                    if roas is not None
                    else None,
            },

            "ad_groups": {

                "total":
                    total_ad_groups,

                "enabled":
                    enabled_ad_groups,

                "paused":
                    paused_ad_groups,
            },

            "health": {

                "score":
                    health_score,

                "status":
                    health_status,

                "strengths":
                    strengths,

                "warnings":
                    warnings,

                "recommendations":
                    recommendations,
            },
        }

    except ValueError as error:

        return {
            "status": "FAILED",
            "error": str(error),
        }

    except Exception as error:

        return {
            "status": "FAILED",
            "error": str(error),
        }
# ----------------------------------------------------
# PREVIEW BUDGET UPDATE
# ----------------------------------------------------

@app.post("/preview-budget-update")
def preview_budget_update(
    request: BudgetUpdateRequest
):
    try:

        customer_id = normalize_customer_id(
            request.customer_id
        )

        client = get_google_ads_client()

        google_ads_service = client.get_service(
            "GoogleAdsService"
        )

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign_budget.amount_micros
            FROM campaign
            WHERE campaign.id = {request.campaign_id}
        """

        response = google_ads_service.search(
            customer_id=customer_id,
            query=query
        )

        row = next(iter(response), None)

        if not row:
            return {
                "error": "Campaign not found"
            }

        current_budget = (
            row.campaign_budget.amount_micros
            / 1000000
        )

        return {
            "campaign_id": str(
                row.campaign.id
            ),
            "campaign_name":
                row.campaign.name,
            "current_budget":
                round(current_budget, 2),
            "new_budget":
                request.new_budget,
            "delta":
                round(
                    request.new_budget
                    - current_budget,
                    2
                ),
            "will_change": True
        }

    except Exception as error:
        return {
            "error": str(error)
        }

# ============================================================
# ACCOUNTS
# ============================================================

@app.get("/accounts")
def accounts():

    try:

        client = get_google_ads_client()

        customer_service = client.get_service(
            "CustomerService"
        )

        google_ads_service = client.get_service(
            "GoogleAdsService"
        )

        accessible_customers = (
            customer_service.list_accessible_customers()
        )

        results = []

        for resource_name in (
            accessible_customers.resource_names
        ):

            customer_id = (
                resource_name.split("/")[-1]
            )

            query = """
                SELECT
                    customer.id,
                    customer.descriptive_name,
                    customer.currency_code,
                    customer.time_zone,
                    customer.manager
                FROM customer
            """

            try:

                response = (
                    google_ads_service.search(
                        customer_id=customer_id,
                        query=query
                    )
                )

                for row in response:

                    results.append(
                        {
                            "customer_id": str(
                                row.customer.id
                            ),
                            "account_name":
                                row.customer.descriptive_name,
                            "currency":
                                row.customer.currency_code,
                            "time_zone":
                                row.customer.time_zone,
                            "is_manager":
                                row.customer.manager
                        }
                    )

            except Exception:
                pass

        results.sort(
            key=lambda x:
                x["account_name"].lower()
        )

        return {
            "total_accounts": len(results),
            "accounts": results
        }

    except Exception as error:

        return {
            "error": str(error)
        }
# ============================================================
# ACCOUNT-SEARCH
# ============================================================
@app.get("/account-search")
def account_search(
    name: str
):
    try:

        client = get_google_ads_client()

        customer_service = client.get_service(
            "CustomerService"
        )

        google_ads_service = client.get_service(
            "GoogleAdsService"
        )

        search_value = (
            name.strip()
            .lower()
        )

        results = []

        accessible_customers = (
            customer_service.list_accessible_customers()
        )

        for resource_name in (
            accessible_customers.resource_names
        ):

            customer_id = (
                resource_name.split("/")[-1]
            )

            query = """
                SELECT
                    customer.id,
                    customer.descriptive_name,
                    customer.currency_code,
                    customer.time_zone,
                    customer.manager
                FROM customer
            """

            try:

                response = (
                    google_ads_service.search(
                        customer_id=customer_id,
                        query=query
                    )
                )

                for row in response:

                    account_name = (
                        row.customer.descriptive_name
                        or ""
                    )

                    if (
                        search_value
                        in account_name.lower()
                    ):

                        results.append(
                            {
                                "customer_id": str(
                                    row.customer.id
                                ),
                                "account_name":
                                    account_name,
                                "currency":
                                    row.customer.currency_code,
                                "time_zone":
                                    row.customer.time_zone,
                                "is_manager":
                                    row.customer.manager
                            }
                        )

            except Exception:
                pass

        results.sort(
            key=lambda x:
            x["account_name"].lower()
        )

        return {
            "search": name,
            "matches_found": len(results),
            "matches": results
        }

    except Exception as error:

        return {
            "error": str(error)
        }

# ============================================================
# AD-GROUPE-SEARCH
# ============================================================
@app.get("/ad-group-search")
def ad_group_search(
    customer_id: str,
    campaign_id: str,
    name: str
):
    try:
        customer_id = normalize_customer_id(
            customer_id
        )

        campaign_id = (
            campaign_id
            .replace("-", "")
            .strip()
        )

        search_value = (
            name.strip()
            .lower()
        )

        client = get_google_ads_client()

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.type
            FROM ad_group
            WHERE campaign.id = {campaign_id}
            ORDER BY ad_group.name
        """

        response = execute_query(
            client,
            customer_id,
            query
        )

        matches = []

        for row in response:
            ad_group_name = (
                row.ad_group.name or ""
            )

            if search_value in ad_group_name.lower():
                matches.append(
                    {
                        "customer_id": customer_id,
                        "campaign_id": str(
                            row.campaign.id
                        ),
                        "campaign_name": (
                            row.campaign.name
                        ),
                        "ad_group_id": str(
                            row.ad_group.id
                        ),
                        "ad_group_name": (
                            ad_group_name
                        ),
                        "status": enum_name(
                            row.ad_group.status
                        ),
                        "type": enum_name(
                            row.ad_group.type
                        )
                    }
                )

        return {
            "customer_id": customer_id,
            "campaign_id": campaign_id,
            "search": name,
            "matches_found": len(matches),
            "matches": matches
        }

    except Exception as error:
        return {
            "status": "FAILED",
            "error": str(error)
        }
# ============================================================
# CAMPAGNES-SEARCH
# ============================================================
@app.get("/campaign-search")
def campaign_search(
    customer_id: str,
    name: str
):
    try:

        customer_id = normalize_customer_id(
            customer_id
        )

        search_value = (
            name.strip()
            .lower()
        )

        client = get_google_ads_client()

        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type
            FROM campaign
            ORDER BY campaign.name
        """

        response = execute_query(
            client,
            customer_id,
            query
        )

        matches = []

        for row in response:

            campaign_name = (
                row.campaign.name or ""
            )

            if (
                search_value
                in campaign_name.lower()
            ):

                matches.append(
                    {
                        "campaign_id": str(
                            row.campaign.id
                        ),
                        "campaign_name":
                            campaign_name,
                        "status": enum_name(
                            row.campaign.status
                        ),
                        "channel_type":
                            enum_name(
                                row.campaign
                                .advertising_channel_type
                            )
                    }
                )

        return {
            "customer_id": customer_id,
            "search": name,
            "matches_found": len(matches),
            "matches": matches
        }

    except Exception as error:

        return {
            "error": str(error)
        }
# ============================================================
# CAMPAGNES
# ============================================================

@app.get("/campaigns")
def campaigns(
    customer_id: str
):

    try:
        client = get_google_ads_client()
        customer_id = normalize_customer_id(
                customer_id
        )

        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type
            FROM campaign
            ORDER BY campaign.name
        """

        response = execute_query(
client,
customer_id,
query
)

        data = []

        for row in response:
            data.append(
                {
                    "campaign_id": str(row.campaign.id),
                    "campaign_name": row.campaign.name,
                    "status": enum_name(row.campaign.status),
                    "channel_type": enum_name(
                        row.campaign.advertising_channel_type
                    ),
                }
            )

        return data

    except Exception as error:
        return {"error": str(error)}

# ============================================================
# PERFORMANCE DES CAMPAGNES
# ============================================================

@app.get("/campaign-performance")
def campaign_performance(
    customer_id: str = Query(
        ...,
        description="ID du compte Google Ads",
    ),
    period: str = Query(
        default="LAST_30_DAYS",
        description=(
            "Période Google Ads prédéfinie."
        ),
    ),
    start_date: Optional[str] = Query(
        default=None,
        description=(
            "Date de début personnalisée "
            "au format YYYY-MM-DD."
        ),
    ),
    end_date: Optional[str] = Query(
        default=None,
        description=(
            "Date de fin personnalisée "
            "au format YYYY-MM-DD."
        ),
    ),
):
    try:

        customer_id = normalize_customer_id(
            customer_id
        )

        date_configuration = (
            build_date_filter(
                period=period,
                start_date=start_date,
                end_date=end_date,
            )
        )

        date_filter = (
            date_configuration["filter"]
        )

        date_range = {
            "mode": (
                date_configuration["mode"]
            ),
            "period": (
                date_configuration["period"]
            ),
            "start_date": (
                date_configuration["start_date"]
            ),
            "end_date": (
                date_configuration["end_date"]
            ),
        }

        client = get_google_ads_client()

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign_budget.amount_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.average_cpc,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.conversions_from_interactions_rate
            FROM campaign
            WHERE campaign.status != 'REMOVED'
              AND {date_filter}
            ORDER BY metrics.cost_micros DESC
        """

        response = execute_query(
            client,
            customer_id,
            query,
        )

        data = []

        for row in response:

            cost = (
                row.metrics.cost_micros
                / 1_000_000
            )

            conversions = safe_float(
                row.metrics.conversions
            )

            conversion_value = safe_float(
                row.metrics.conversions_value
            )

            average_cpc = (
                row.metrics.average_cpc
                / 1_000_000
            )

            conversion_rate = (
                safe_float(
                    row.metrics
                    .conversions_from_interactions_rate
                )
                * 100
            )

            daily_budget = (
                row.campaign_budget.amount_micros
                / 1_000_000
            )

            cpa = (
                round(
                    cost / conversions,
                    2,
                )
                if conversions > 0
                else None
            )

            roas = (
                round(
                    conversion_value / cost,
                    2,
                )
                if cost > 0
                else None
            )

            data.append(
                {
                    "campaign_id": str(
                        row.campaign.id
                    ),

                    "campaign_name": (
                        row.campaign.name
                    ),

                    "status": enum_name(
                        row.campaign.status
                    ),

                    "channel_type": enum_name(
                        row.campaign
                        .advertising_channel_type
                    ),

                    "daily_budget": round(
                        daily_budget,
                        2,
                    ),

                    "impressions": (
                        row.metrics.impressions
                    ),

                    "clicks": (
                        row.metrics.clicks
                    ),

                    "ctr_percent": round(
                        safe_float(
                            row.metrics.ctr
                        )
                        * 100,
                        2,
                    ),

                    "average_cpc": round(
                        average_cpc,
                        2,
                    ),

                    "cost": round(
                        cost,
                        2,
                    ),

                    "conversions": round(
                        conversions,
                        2,
                    ),

                    "conversion_rate_percent": round(
                        conversion_rate,
                        2,
                    ),

                    "conversion_value": round(
                        conversion_value,
                        2,
                    ),

                    "cpa": cpa,

                    "roas": roas,
                }
            )

        total_cost = round(
            sum(
                campaign["cost"]
                for campaign in data
            ),
            2,
        )

        total_conversions = round(
            sum(
                campaign["conversions"]
                for campaign in data
            ),
            2,
        )

        total_conversion_value = round(
            sum(
                campaign["conversion_value"]
                for campaign in data
            ),
            2,
        )

        account_roas = (
            round(
                total_conversion_value
                / total_cost,
                2,
            )
            if total_cost > 0
            else None
        )

        account_cpa = (
            round(
                total_cost
                / total_conversions,
                2,
            )
            if total_conversions > 0
            else None
        )

        return {
            "status": "SUCCESS",

            "customer_id": customer_id,

            "date_range": date_range,

            "summary": {
                "campaigns_count": len(
                    data
                ),
                "total_cost": total_cost,
                "total_conversions": (
                    total_conversions
                ),
                "total_conversion_value": (
                    total_conversion_value
                ),
                "account_cpa": (
                    account_cpa
                ),
                "account_roas": (
                    account_roas
                ),
            },

            "campaigns": data,
        }

    except ValueError as error:

        return {
            "status": "FAILED",
            "error": str(error),
        }

    except Exception as error:

        return {
            "status": "FAILED",
            "error": str(error),
        }
# ============================================================
# TOP CAMPAGNES
# ============================================================

@app.get("/top-campaigns")
def top_campaigns(
    customer_id: str = Query(
        ...,
        description="ID du compte Google Ads",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
    ),
    period: str = Query(
        default="LAST_30_DAYS",
    ),
    start_date: Optional[str] = Query(
        default=None,
    ),
    end_date: Optional[str] = Query(
        default=None,
    ),
):
    performance = campaign_performance(
        customer_id=customer_id,
        period=period,
        start_date=start_date,
        end_date=end_date,
    )

    if (
        not isinstance(performance, dict)
        or performance.get("status") != "SUCCESS"
    ):
        return performance

    campaigns = performance.get(
        "campaigns",
        [],
    )

    campaigns_with_roas = [
        campaign
        for campaign in campaigns
        if campaign.get("roas") is not None
    ]

    campaigns_with_roas.sort(
        key=lambda value: value["roas"],
        reverse=True,
    )

    return {
        "status": "SUCCESS",

        "customer_id": customer_id,

        "date_range": performance.get(
            "date_range"
        ),

        "summary": {
            "total_campaigns": len(
                campaigns
            ),
            "campaigns_with_roas": len(
                campaigns_with_roas
            ),
            "limit": limit,
        },

        "top_campaigns": (
            campaigns_with_roas[:limit]
        ),
    }
# ============================================================
# MOTS-CLÉS
# ============================================================
@app.get("/keywords")
def keywords(
    customer_id: str,
    period: str = Query(
        default="LAST_30_DAYS",
        description="Période Google Ads prédéfinie",
    ),
    start_date: Optional[str] = Query(
        default=None,
        description="Date de début YYYY-MM-DD",
    ),
    end_date: Optional[str] = Query(
        default=None,
        description="Date de fin YYYY-MM-DD",
    ),
):
    try:
        client = get_google_ads_client()

        customer_id = normalize_customer_id(
            customer_id
        )

        date_configuration = build_date_filter(
            period=period,
            start_date=start_date,
            end_date=end_date,
        )

        date_filter = (
            date_configuration["filter"]
        )

        date_range = {
            "mode": (
                date_configuration["mode"]
            ),
            "period": (
                date_configuration["period"]
            ),
            "start_date": (
                date_configuration["start_date"]
            ),
            "end_date": (
                date_configuration["end_date"]
            ),
        }

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.average_cpc,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.conversions_from_interactions_rate
            FROM keyword_view
            WHERE ad_group_criterion.status != 'REMOVED'
              AND {date_filter}
        """

        response = execute_query(
            client,
            customer_id,
            query,
        )

        data = []

        for row in response:

            cost = (
                row.metrics.cost_micros
                / 1_000_000
            )

            conversions = safe_float(
                row.metrics.conversions
            )

            conversion_value = safe_float(
                row.metrics.conversions_value
            )

            average_cpc = (
                row.metrics.average_cpc
                / 1_000_000
            )

            ctr = (
                safe_float(
                    row.metrics.ctr
                )
                * 100
            )

            conversion_rate = (
                safe_float(
                    row.metrics
                    .conversions_from_interactions_rate
                )
                * 100
            )

            cpa = (
                round(
                    cost / conversions,
                    2,
                )
                if conversions > 0
                else None
            )

            roas = (
                round(
                    conversion_value / cost,
                    2,
                )
                if cost > 0
                else None
            )

            data.append(
                {
                    "campaign_id": str(
                        row.campaign.id
                    ),
                    "campaign": (
                        row.campaign.name
                    ),
                    "ad_group_id": str(
                        row.ad_group.id
                    ),
                    "ad_group": (
                        row.ad_group.name
                    ),
                    "criterion_id": str(
                        row.ad_group_criterion
                        .criterion_id
                    ),
                    "keyword": (
                        row.ad_group_criterion
                        .keyword
                        .text
                    ),
                    "match_type": enum_name(
                        row.ad_group_criterion
                        .keyword
                        .match_type
                    ),
                    "status": enum_name(
                        row.ad_group_criterion
                        .status
                    ),
                    "impressions": (
                        row.metrics.impressions
                    ),
                    "clicks": (
                        row.metrics.clicks
                    ),
                    "ctr_percent": round(
                        ctr,
                        2,
                    ),
                    "average_cpc": round(
                        average_cpc,
                        2,
                    ),
                    "cost": round(
                        cost,
                        2,
                    ),
                    "conversions": round(
                        conversions,
                        2,
                    ),
                    "conversion_rate_percent": round(
                        conversion_rate,
                        2,
                    ),
                    "conversion_value": round(
                        conversion_value,
                        2,
                    ),
                    "cpa": cpa,
                    "roas": roas,
                }
            )

        return {
            "customer_id": customer_id,
            "date_range": date_range,
            "total_keywords": len(data),
            "keywords": data,
        }

    except ValueError as error:
        return {
            "error": str(error),
            "customer_id": customer_id,
        }

    except Exception as error:
        return {
            "error": str(error),
            "customer_id": customer_id,
        }

# ============================================================
# TOP KEYWORDS
# ============================================================

@app.get("/top-keywords")
def top_keywords(
    customer_id: str = Query(
        ...,
        description="ID du compte Google Ads",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    ranking_by: str = Query(
        default="ROAS",
        description=(
            "ROAS | CPA | CONVERSIONS | "
            "CONVERSION_VALUE | CTR | "
            "CLICKS | COST | IMPRESSIONS | "
            "CONVERSION_RATE | AVG_CPC"
        ),
    ),
    period: str = Query(
        default="LAST_30_DAYS",
    ),
    start_date: Optional[str] = Query(
        default=None,
    ),
    end_date: Optional[str] = Query(
        default=None,
    ),
):
    try:

        customer_id = normalize_customer_id(
            customer_id
        )

        ranking_by = (
            ranking_by.upper().strip()
        )

        valid_metrics = {
            "ROAS",
            "CPA",
            "CONVERSIONS",
            "CONVERSION_VALUE",
            "CTR",
            "CLICKS",
            "COST",
            "IMPRESSIONS",
            "CONVERSION_RATE",
            "AVG_CPC",
        }

        if ranking_by not in valid_metrics:
            return {
                "status": "FAILED",
                "error": (
                    f"ranking_by invalide. "
                    f"Valeurs acceptées : "
                    f"{sorted(valid_metrics)}"
                ),
            }

        date_configuration = (
            build_date_filter(
                period=period,
                start_date=start_date,
                end_date=end_date,
            )
        )

        date_filter = (
            date_configuration["filter"]
        )

        date_range = {
            "mode": (
                date_configuration["mode"]
            ),
            "period": (
                date_configuration["period"]
            ),
            "start_date": (
                date_configuration["start_date"]
            ),
            "end_date": (
                date_configuration["end_date"]
            ),
        }

        client = get_google_ads_client()

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.average_cpc,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.conversions_from_interactions_rate
            FROM keyword_view
            WHERE ad_group_criterion.status != 'REMOVED'
              AND {date_filter}
        """

        response = execute_query(
            client,
            customer_id,
            query,
        )

        keywords = []

        for row in response:

            cost = (
                row.metrics.cost_micros
                / 1_000_000
            )

            conversions = safe_float(
                row.metrics.conversions
            )

            conversion_value = safe_float(
                row.metrics.conversions_value
            )

            average_cpc = (
                row.metrics.average_cpc
                / 1_000_000
            )

            ctr = (
                safe_float(
                    row.metrics.ctr
                )
                * 100
            )

            conversion_rate = (
                safe_float(
                    row.metrics
                    .conversions_from_interactions_rate
                )
                * 100
            )

            cpa = (
                round(
                    cost / conversions,
                    2,
                )
                if conversions > 0
                else None
            )

            roas = (
                round(
                    conversion_value / cost,
                    2,
                )
                if cost > 0
                else None
            )

            keywords.append(
                {
                    "campaign_id": str(
                        row.campaign.id
                    ),
                    "campaign_name": (
                        row.campaign.name
                    ),
                    "ad_group_id": str(
                        row.ad_group.id
                    ),
                    "ad_group_name": (
                        row.ad_group.name
                    ),
                    "criterion_id": str(
                        row.ad_group_criterion
                        .criterion_id
                    ),
                    "keyword": (
                        row.ad_group_criterion
                        .keyword.text
                    ),
                    "match_type": enum_name(
                        row.ad_group_criterion
                        .keyword.match_type
                    ),
                    "status": enum_name(
                        row.ad_group_criterion
                        .status
                    ),
                    "impressions": (
                        row.metrics.impressions
                    ),
                    "clicks": (
                        row.metrics.clicks
                    ),
                    "ctr": round(
                        ctr,
                        2,
                    ),
                    "average_cpc": round(
                        average_cpc,
                        2,
                    ),
                    "cost": round(
                        cost,
                        2,
                    ),
                    "conversions": round(
                        conversions,
                        2,
                    ),
                    "conversion_rate": round(
                        conversion_rate,
                        2,
                    ),
                    "conversion_value": round(
                        conversion_value,
                        2,
                    ),
                    "cpa": cpa,
                    "roas": roas,
                }
            )

        metric_field = {
            "ROAS": "roas",
            "CPA": "cpa",
            "CONVERSIONS": "conversions",
            "CONVERSION_VALUE": (
                "conversion_value"
            ),
            "CTR": "ctr",
            "CLICKS": "clicks",
            "COST": "cost",
            "IMPRESSIONS": (
                "impressions"
            ),
            "CONVERSION_RATE": (
                "conversion_rate"
            ),
            "AVG_CPC": (
                "average_cpc"
            ),
        }

        metric_name = (
            metric_field[ranking_by]
        )

        ranked_keywords = [
            keyword
            for keyword in keywords
            if keyword.get(metric_name)
            is not None
        ]

        reverse_sort = ranking_by != "CPA"

        ranked_keywords.sort(
            key=lambda item: (
                item[metric_name]
            ),
            reverse=reverse_sort,
        )

        return {
            "status": "SUCCESS",

            "customer_id": customer_id,

            "date_range": date_range,

            "summary": {
                "keywords_analyzed": len(
                    keywords
                ),
                "ranked_keywords": len(
                    ranked_keywords
                ),
                "limit": limit,
                "ranking_by": (
                    ranking_by
                ),
            },

            "top_keywords": (
                ranked_keywords[:limit]
            ),
        }

    except ValueError as error:

        return {
            "status": "FAILED",
            "error": str(error),
        }

    except Exception as error:

        return {
            "status": "FAILED",
            "error": str(error),
        }

# ============================================================
# ADS
# ============================================================

@app.get("/ads")
def ads(
    customer_id: str = Query(
        ...,
        description="ID du compte Google Ads",
    ),
    period: str = Query(
        default="LAST_30_DAYS",
        description="Période Google Ads",
    ),
    start_date: Optional[str] = Query(
        default=None,
        description="Date de début YYYY-MM-DD",
    ),
    end_date: Optional[str] = Query(
        default=None,
        description="Date de fin YYYY-MM-DD",
    ),
):
    try:

        customer_id = normalize_customer_id(
            customer_id
        )

        date_configuration = (
            build_date_filter(
                period=period,
                start_date=start_date,
                end_date=end_date,
            )
        )

        date_filter = (
            date_configuration["filter"]
        )

        date_range = {
            "mode": (
                date_configuration["mode"]
            ),
            "period": (
                date_configuration["period"]
            ),
            "start_date": (
                date_configuration["start_date"]
            ),
            "end_date": (
                date_configuration["end_date"]
            ),
        }

        client = get_google_ads_client()

        query = f"""
            SELECT
                campaign.id,
                campaign.name,

                ad_group.id,
                ad_group.name,

                ad_group_ad.ad.id,
                ad_group_ad.status,
                ad_group_ad.ad.type,
                ad_group_ad.ad_strength,

                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.average_cpc,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.conversions_from_interactions_rate

            FROM ad_group_ad

            WHERE ad_group_ad.status != 'REMOVED'
              AND {date_filter}

            ORDER BY metrics.cost_micros DESC
        """

        response = execute_query(
            client,
            customer_id,
            query,
        )

        ads_data = []

        for row in response:

            cost = (
                row.metrics.cost_micros
                / 1_000_000
            )

            conversions = safe_float(
                row.metrics.conversions
            )

            conversion_value = safe_float(
                row.metrics.conversions_value
            )

            average_cpc = (
                row.metrics.average_cpc
                / 1_000_000
            )

            ctr = (
                safe_float(
                    row.metrics.ctr
                )
                * 100
            )

            conversion_rate = (
                safe_float(
                    row.metrics
                    .conversions_from_interactions_rate
                )
                * 100
            )

            cpa = (
                round(
                    cost / conversions,
                    2,
                )
                if conversions > 0
                else None
            )

            roas = (
                round(
                    conversion_value / cost,
                    2,
                )
                if cost > 0
                else None
            )

            ads_data.append(
                {
                    "campaign_id": str(
                        row.campaign.id
                    ),

                    "campaign_name": (
                        row.campaign.name
                    ),

                    "ad_group_id": str(
                        row.ad_group.id
                    ),

                    "ad_group_name": (
                        row.ad_group.name
                    ),

                    "ad_id": str(
                        row.ad_group_ad.ad.id
                    ),

                    "status": enum_name(
                        row.ad_group_ad.status
                    ),

                    "ad_type": enum_name(
                        row.ad_group_ad.ad.type
                    ),

                    "ad_strength": enum_name(
                        row.ad_group_ad.ad_strength
                    ),

                    "impressions": (
                        row.metrics.impressions
                    ),

                    "clicks": (
                        row.metrics.clicks
                    ),

                    "ctr_percent": round(
                        ctr,
                        2,
                    ),

                    "average_cpc": round(
                        average_cpc,
                        2,
                    ),

                    "cost": round(
                        cost,
                        2,
                    ),

                    "conversions": round(
                        conversions,
                        2,
                    ),

                    "conversion_rate_percent": round(
                        conversion_rate,
                        2,
                    ),

                    "conversion_value": round(
                        conversion_value,
                        2,
                    ),

                    "cpa": cpa,

                    "roas": roas,
                }
            )

        total_cost = round(
            sum(
                ad["cost"]
                for ad in ads_data
            ),
            2,
        )

        total_conversions = round(
            sum(
                ad["conversions"]
                for ad in ads_data
            ),
            2,
        )

        total_conversion_value = round(
            sum(
                ad["conversion_value"]
                for ad in ads_data
            ),
            2,
        )

        account_roas = (
            round(
                total_conversion_value
                / total_cost,
                2,
            )
            if total_cost > 0
            else None
        )

        account_cpa = (
            round(
                total_cost
                / total_conversions,
                2,
            )
            if total_conversions > 0
            else None
        )

        return {
            "status": "SUCCESS",

            "customer_id": customer_id,

            "date_range": date_range,

            "summary": {
                "ads_count": len(
                    ads_data
                ),
                "total_cost": total_cost,
                "total_conversions": (
                    total_conversions
                ),
                "total_conversion_value": (
                    total_conversion_value
                ),
                "account_cpa": (
                    account_cpa
                ),
                "account_roas": (
                    account_roas
                ),
            },

            "ads": ads_data,
        }

    except ValueError as error:

        return {
            "status": "FAILED",
            "error": str(error),
        }

    except Exception as error:

        return {
            "status": "FAILED",
            "error": str(error),
        }
# ============================================================
# SEARCH TERMS
# ============================================================

@app.get("/search-terms")
def search_terms(
    customer_id: str = Query(
        ...,
        description=(
            "ID du compte Google Ads"
        ),
    ),
    campaign_id: str = Query(
        ...,
        description=(
            "ID de la campagne Google Ads"
        ),
    ),
    period: str = Query(
        default="LAST_30_DAYS",
        description=(
            "Période Google Ads prédéfinie."
        ),
    ),
    start_date: Optional[str] = Query(
        default=None,
        description=(
            "Date de début YYYY-MM-DD"
        ),
    ),
    end_date: Optional[str] = Query(
        default=None,
        description=(
            "Date de fin YYYY-MM-DD"
        ),
    ),
):
    try:

        customer_id = normalize_customer_id(
            customer_id
        )

        campaign_id = (
            campaign_id
            .replace("-", "")
            .strip()
        )

        if not campaign_id.isdigit():

            return {
                "status": "FAILED",
                "error": (
                    "campaign_id doit contenir "
                    "uniquement des chiffres."
                ),
            }

        date_configuration = (
            build_date_filter(
                period=period,
                start_date=start_date,
                end_date=end_date,
            )
        )

        date_filter = (
            date_configuration["filter"]
        )

        date_range = {
            "mode": (
                date_configuration["mode"]
            ),
            "period": (
                date_configuration["period"]
            ),
            "start_date": (
                date_configuration["start_date"]
            ),
            "end_date": (
                date_configuration["end_date"]
            ),
        }

        client = get_google_ads_client()

        google_ads_service = (
            client.get_service(
                "GoogleAdsService"
            )
        )

        query = f"""
            SELECT
                campaign.id,
                campaign.name,

                ad_group.id,
                ad_group.name,

                search_term_view.search_term,

                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.average_cpc,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.conversions_from_interactions_rate

            FROM search_term_view

            WHERE campaign.id = {campaign_id}
              AND {date_filter}

            ORDER BY metrics.cost_micros DESC
        """

        response = google_ads_service.search(
            customer_id=customer_id,
            query=query,
        )

        results = []
        campaign_name = ""

        for row in response:

            campaign_name = (
                row.campaign.name
            )

            cost = (
                row.metrics.cost_micros
                / 1_000_000
            )

            conversions = safe_float(
                row.metrics.conversions
            )

            conversion_value = safe_float(
                row.metrics.conversions_value
            )

            average_cpc = (
                row.metrics.average_cpc
                / 1_000_000
            )

            ctr = (
                safe_float(
                    row.metrics.ctr
                )
                * 100
            )

            conversion_rate = (
                safe_float(
                    row.metrics
                    .conversions_from_interactions_rate
                )
                * 100
            )

            cpa = (
                cost / conversions
                if conversions > 0
                else None
            )

            roas = (
                conversion_value / cost
                if cost > 0
                else None
            )

            results.append(
                {
                    "campaign_id": str(
                        row.campaign.id
                    ),

                    "campaign_name": (
                        row.campaign.name
                    ),

                    "ad_group_id": str(
                        row.ad_group.id
                    ),

                    "ad_group_name": (
                        row.ad_group.name
                    ),

                    "search_term": (
                        row.search_term_view
                        .search_term
                    ),

                    "impressions": (
                        row.metrics.impressions
                    ),

                    "clicks": (
                        row.metrics.clicks
                    ),

                    "ctr_percent": round(
                        ctr,
                        2,
                    ),

                    "average_cpc": round(
                        average_cpc,
                        2,
                    ),

                    "cost": round(
                        cost,
                        2,
                    ),

                    "conversions": round(
                        conversions,
                        2,
                    ),

      
# ============================================================
# SEARCH TERM OPPORTUNITIES V2
# Analyse en lecture seule des termes de recherche
# Prend en compte le statut Ajouté / Exclu
# AUCUNE modification automatique
# ============================================================

@app.get("/search-term-opportunities")
def search_term_opportunities(
    customer_id: str = Query(
        ...,
        description="ID du compte Google Ads",
    ),
    campaign_id: str = Query(
        ...,
        description="ID de la campagne Google Ads",
    ),
    period: str = Query(
        default="LAST_30_DAYS",
        description=(
            "Période Google Ads prédéfinie. "
            "LAST_30_DAYS par défaut."
        ),
    ),
    start_date: Optional[str] = Query(
        default=None,
        description=(
            "Date de début personnalisée "
            "au format YYYY-MM-DD."
        ),
    ),
    end_date: Optional[str] = Query(
        default=None,
        description=(
            "Date de fin personnalisée "
            "au format YYYY-MM-DD."
        ),
    ),
    minimum_clicks: int = Query(
        default=5,
        ge=1,
        le=1000,
        description=(
            "Nombre minimum de clics avant "
            "de générer une opportunité."
        ),
    ),
    minimum_cost: float = Query(
        default=10.0,
        ge=0,
        description=(
            "Coût minimum sans conversion "
            "avant de générer une opportunité."
        ),
    ),
    high_cpa_multiplier: float = Query(
        default=1.5,
        ge=1.0,
        le=10.0,
        description=(
            "Multiplicateur du CPA moyen utilisé "
            "pour détecter un CPA élevé."
        ),
    ),
):
    try:
        customer_id = normalize_customer_id(
            customer_id
        )

        campaign_id = (
            campaign_id
            .replace("-", "")
            .strip()
        )

        if not campaign_id.isdigit():
            return {
                "status": "FAILED",
                "error": (
                    "campaign_id doit contenir "
                    "uniquement des chiffres."
                ),
            }

        date_configuration = build_date_filter(
            period=period,
            start_date=start_date,
            end_date=end_date,
        )

        date_filter = (
            date_configuration["filter"]
        )

        client = get_google_ads_client()

        google_ads_service = client.get_service(
            "GoogleAdsService"
        )

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                search_term_view.search_term,
                search_term_view.status,
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.average_cpc,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.conversions_from_interactions_rate
            FROM search_term_view
            WHERE campaign.id = {campaign_id}
              AND {date_filter}
            ORDER BY metrics.cost_micros DESC
        """

        response = google_ads_service.search(
            customer_id=customer_id,
            query=query,
        )

        search_terms = []
        campaign_name = ""

        total_cost = 0.0
        total_conversions = 0.0
        total_conversion_value = 0.0
        total_clicks = 0
        total_impressions = 0

        for row in response:
            campaign_name = (
                row.campaign.name
            )

            targeting_status = enum_name(
                row.search_term_view.status
            )

            cost = (
                row.metrics.cost_micros
                / 1_000_000
            )

            conversions = safe_float(
                row.metrics.conversions
            )

            conversion_value = safe_float(
                row.metrics.conversions_value
            )

            average_cpc = (
                row.metrics.average_cpc
                / 1_000_000
            )

            ctr = (
                safe_float(row.metrics.ctr)
                * 100
            )

            conversion_rate = (
                safe_float(
                    row.metrics
                    .conversions_from_interactions_rate
                )
                * 100
            )

            cpa = (
                cost / conversions
                if conversions > 0
                else None
            )

            roas = (
                conversion_value / cost
                if cost > 0
                else None
            )

            total_cost += cost
            total_conversions += conversions
            total_conversion_value += (
                conversion_value
            )
            total_clicks += (
                row.metrics.clicks
            )
            total_impressions += (
                row.metrics.impressions
            )

            is_already_added = (
                targeting_status
                in {
                    "ADDED",
                    "ADDED_EXCLUDED",
                }
            )

            is_already_excluded = (
                targeting_status
                in {
                    "EXCLUDED",
                    "ADDED_EXCLUDED",
                }
            )

            is_available_for_action = (
                targeting_status == "NONE"
            )

            search_terms.append(
                {
                    "campaign_id": str(
                        row.campaign.id
                    ),
                    "campaign_name": (
                        row.campaign.name
                    ),
                    "ad_group_id": str(
                        row.ad_group.id
                    ),
                    "ad_group_name": (
                        row.ad_group.name
                    ),
                    "search_term": (
                        row.search_term_view
                        .search_term
                    ),
                    "targeting_status": (
                        targeting_status
                    ),
                    "is_already_added": (
                        is_already_added
                    ),
                    "is_already_excluded": (
                        is_already_excluded
                    ),
                    "is_available_for_action": (
                        is_available_for_action
                    ),
                    "impressions": (
                        row.metrics.impressions
                    ),
                    "clicks": (
                        row.metrics.clicks
                    ),
                    "ctr_percent": round(
                        ctr,
                        2
                    ),
                    "average_cpc": round(
                        average_cpc,
                        2
                    ),
                    "cost": round(
                        cost,
                        2
                    ),
                    "conversions": round(
                        conversions,
                        2
                    ),
                    "conversion_rate_percent": (
                        round(
                            conversion_rate,
                            2
                        )
                    ),
                    "conversion_value": round(
                        conversion_value,
                        2
                    ),
                    "cpa": (
                        round(cpa, 2)
                        if cpa is not None
                        else None
                    ),
                    "roas": (
                        round(roas, 2)
                        if roas is not None
                        else None
                    ),
                }
            )

        if not search_terms:
            return {
                "status": "NO_DATA",
                "customer_id": customer_id,
                "campaign_id": campaign_id,
                "date_range": {
                    "mode": (
                        date_configuration["mode"]
                    ),
                    "period": (
                        date_configuration["period"]
                    ),
                    "start_date": (
                        date_configuration[
                            "start_date"
                        ]
                    ),
                    "end_date": (
                        date_configuration[
                            "end_date"
                        ]
                    ),
                },
                "message": (
                    "Aucun terme de recherche "
                    "n'a été retourné pour cette "
                    "campagne et cette période."
                ),
                "automatic_action": False,
            }

        campaign_average_cpa = (
            total_cost / total_conversions
            if total_conversions > 0
            else None
        )

        campaign_roas = (
            total_conversion_value / total_cost
            if total_cost > 0
            else None
        )

        # ----------------------------------------------------
        # TERMES DÉJÀ AJOUTÉS
        # ----------------------------------------------------

        already_added_keywords = [
            {
                **item,
                "opportunity_type": (
                    "EXISTING_KEYWORD"
                ),
                "recommendation": (
                    "Ce terme est déjà ajouté comme "
                    "mot-clé. Ne pas proposer un nouvel "
                    "ajout. Évaluer uniquement sa "
                    "performance actuelle."
                ),
            }
            for item in search_terms
            if item["is_already_added"]
        ]

        already_added_keywords.sort(
            key=lambda item: item["cost"],
            reverse=True,
        )

        # ----------------------------------------------------
        # TERMES DÉJÀ EXCLUS
        # ----------------------------------------------------

        already_excluded_terms = [
            {
                **item,
                "opportunity_type": (
                    "EXISTING_NEGATIVE_KEYWORD"
                ),
                "recommendation": (
                    "Ce terme est déjà exclu. "
                    "Ne pas proposer une nouvelle exclusion."
                ),
            }
            for item in search_terms
            if item["is_already_excluded"]
        ]

        already_excluded_terms.sort(
            key=lambda item: item["cost"],
            reverse=True,
        )

        # ----------------------------------------------------
        # DÉPENSE SANS CONVERSION
        # Seulement si le terme n'est ni ajouté ni exclu
        # ----------------------------------------------------

        negative_keyword_candidates = []

        for item in search_terms:
            if (
                item["is_available_for_action"]
                and item["clicks"] >= minimum_clicks
                and item["cost"] >= minimum_cost
                and item["conversions"] == 0
            ):
                negative_keyword_candidates.append(
                    {
                        **item,
                        "priority": "HIGH",
                        "opportunity_type": (
                            "NEGATIVE_KEYWORD_CANDIDATE"
                        ),
                        "recommendation": (
                            "Vérifier l'intention de recherche "
                            "et la valeur commerciale. Évaluer "
                            "l'ajout comme mot-clé négatif après "
                            "validation humaine."
                        ),
                    }
                )

        negative_keyword_candidates.sort(
            key=lambda item: item["cost"],
            reverse=True,
        )

        # ----------------------------------------------------
        # CPA ÉLEVÉ
        # Tous les statuts sont conservés pour analyse,
        # mais la recommandation dépend du statut existant
        # ----------------------------------------------------

        high_cpa_terms = []

        if campaign_average_cpa is not None:
            high_cpa_threshold = (
                campaign_average_cpa
                * high_cpa_multiplier
            )

            for item in search_terms:
                if (
                    item["clicks"] >= minimum_clicks
                    and item["cpa"] is not None
                    and item["cpa"]
                    > high_cpa_threshold
                ):
                    if item["is_already_excluded"]:
                        recommendation = (
                            "Ce terme est déjà exclu. "
                            "Aucune nouvelle exclusion "
                            "n'est nécessaire."
                        )

                    elif item["is_already_added"]:
                        recommendation = (
                            "Ce terme est déjà ajouté comme "
                            "mot-clé. Vérifier son type de "
                            "correspondance, son enchère, "
                            "l'annonce et la page de destination."
                        )

                    else:
                        recommendation = (
                            "Analyser l'intention, le mot-clé "
                            "déclencheur, l'annonce et la page "
                            "de destination. Ne pas exclure "
                            "automatiquement."
                        )

                    high_cpa_terms.append(
                        {
                            **item,
                            "priority": "MEDIUM",
                            "opportunity_type": (
                                "HIGH_CPA"
                            ),
                            "campaign_average_cpa": (
                                round(
                                    campaign_average_cpa,
                                    2
                                )
                            ),
                            "high_cpa_threshold": (
                                round(
                                    high_cpa_threshold,
                                    2
                                )
                            ),
                            "recommendation": (
                                recommendation
                            ),
                        }
                    )

            high_cpa_terms.sort(
                key=lambda item: item["cpa"],
                reverse=True,
            )

        # ----------------------------------------------------
        # TERMES PERFORMANTS DÉJÀ AJOUTÉS
        # ----------------------------------------------------

        strong_existing_keywords = []

        if campaign_average_cpa is not None:
            for item in search_terms:
                if (
                    item["is_already_added"]
                    and item["clicks"] >= minimum_clicks
                    and item["conversions"] > 0
                    and item["cpa"] is not None
                    and item["cpa"]
                    <= campaign_average_cpa
                ):
                    strong_existing_keywords.append(
                        {
                            **item,
                            "priority": "INFO",
                            "opportunity_type": (
                                "STRONG_EXISTING_KEYWORD"
                            ),
                            "campaign_average_cpa": (
                                round(
                                    campaign_average_cpa,
                                    2
                                )
                            ),
                            "recommendation": (
                                "Terme déjà ajouté comme mot-clé "
                                "et performant. Continuer la "
                                "surveillance. Ne pas créer de "
                                "mot-clé en double."
                            ),
                        }
                    )

            strong_existing_keywords.sort(
                key=lambda item: (
                    item["conversions"],
                    -item["cpa"],
                ),
                reverse=True,
            )

        # ----------------------------------------------------
        # NOUVELLES OPPORTUNITÉS DE MOTS-CLÉS
        # Seulement si statut NONE
        # ----------------------------------------------------

        new_keyword_opportunities = []

        if campaign_average_cpa is not None:
            for item in search_terms:
                if (
                    item["is_available_for_action"]
                    and item["clicks"] >= minimum_clicks
                    and item["conversions"] > 0
                    and item["cpa"] is not None
                    and item["cpa"]
                    <= campaign_average_cpa
                ):
                    new_keyword_opportunities.append(
                        {
                            **item,
                            "priority": "MEDIUM",
                            "opportunity_type": (
                                "NEW_KEYWORD_OPPORTUNITY"
                            ),
                            "campaign_average_cpa": (
                                round(
                                    campaign_average_cpa,
                                    2
                                )
                            ),
                            "recommendation": (
                                "Ce terme n'est ni ajouté ni "
                                "exclu et sa performance est "
                                "supérieure ou égale à la moyenne. "
                                "Évaluer son ajout en mot-clé exact "
                                "ou expression après validation."
                            ),
                        }
                    )

            new_keyword_opportunities.sort(
                key=lambda item: (
                    item["conversions"],
                    -item["cpa"],
                ),
                reverse=True,
            )

        estimated_wasted_cost = round(
            sum(
                item["cost"]
                for item
                in negative_keyword_candidates
            ),
            2,
        )

        total_opportunities = (
            len(negative_keyword_candidates)
            + len(high_cpa_terms)
            + len(new_keyword_opportunities)
        )

        main_risk = (
            "Aucun gaspillage important détecté "
            "parmi les termes non ajoutés et "
            "non exclus."
        )

        recommended_first_action = (
            "Continuer la surveillance des termes "
            "de recherche."
        )

        estimated_priority = "LOW"

        if negative_keyword_candidates:
            top_candidate = (
                negative_keyword_candidates[0]
            )

            main_risk = (
                f"Le terme "
                f"'{top_candidate['search_term']}' "
                f"a coûté {top_candidate['cost']} "
                f"sans conversion et n'est pas "
                f"déjà exclu."
            )

            recommended_first_action = (
                "Vérifier l'intention de ce terme "
                "et évaluer son ajout comme mot-clé "
                "négatif après validation humaine."
            )

            estimated_priority = "HIGH"

        elif high_cpa_terms:
            top_high_cpa_term = (
                high_cpa_terms[0]
            )

            main_risk = (
                f"Le terme "
                f"'{top_high_cpa_term['search_term']}' "
                f"a un CPA de "
                f"{top_high_cpa_term['cpa']}, "
                f"supérieur au CPA moyen de "
                f"{round(campaign_average_cpa, 2)}."
            )

            recommended_first_action = (
                top_high_cpa_term[
                    "recommendation"
                ]
            )

            estimated_priority = "MEDIUM"

        return {
            "status": "SUCCESS",
            "mode": "RECOMMENDATION_ONLY",
            "automatic_action": False,
            "requires_human_confirmation": True,
            "customer_id": customer_id,
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "date_range": {
                "mode": (
                    date_configuration["mode"]
                ),
                "period": (
                    date_configuration["period"]
                ),
                "start_date": (
                    date_configuration[
                        "start_date"
                    ]
                ),
                "end_date": (
                    date_configuration[
                        "end_date"
                    ]
                ),
            },
            "thresholds": {
                "minimum_clicks": (
                    minimum_clicks
                ),
                "minimum_cost": (
                    minimum_cost
                ),
                "high_cpa_multiplier": (
                    high_cpa_multiplier
                ),
            },
            "campaign_summary": {
                "search_terms_analyzed": len(
                    search_terms
                ),
                "impressions": (
                    total_impressions
                ),
                "clicks": total_clicks,
                "cost": round(
                    total_cost,
                    2
                ),
                "conversions": round(
                    total_conversions,
                    2
                ),
                "conversion_value": round(
                    total_conversion_value,
                    2
                ),
                "average_cpa": (
                    round(
                        campaign_average_cpa,
                        2
                    )
                    if campaign_average_cpa
                    is not None
                    else None
                ),
                "roas": (
                    round(campaign_roas, 2)
                    if campaign_roas
                    is not None
                    else None
                ),
            },
            "targeting_status_counts": {
                "already_added": len(
                    already_added_keywords
                ),
                "already_excluded": len(
                    already_excluded_terms
                ),
                "available_for_action": sum(
                    1
                    for item in search_terms
                    if item[
                        "is_available_for_action"
                    ]
                ),
            },
            "executive_summary": {
                "main_risk": main_risk,
                "recommended_first_action": (
                    recommended_first_action
                ),
                "estimated_priority": (
                    estimated_priority
                ),
                "estimated_wasted_cost": (
                    estimated_wasted_cost
                ),
            },
            "opportunity_counts": {
                "total": (
                    total_opportunities
                ),
                "negative_keyword_candidates": (
                    len(
                        negative_keyword_candidates
                    )
                ),
                "high_cpa": len(
                    high_cpa_terms
                ),
                "new_keyword_opportunities": (
                    len(
                        new_keyword_opportunities
                    )
                ),
                "strong_existing_keywords": (
                    len(
                        strong_existing_keywords
                    )
                ),
            },
            "negative_keyword_candidates": (
                negative_keyword_candidates[:50]
            ),
            "new_keyword_opportunities": (
                new_keyword_opportunities[:50]
            ),
            "strong_existing_keywords": (
                strong_existing_keywords[:50]
            ),
            "high_cpa_terms": (
                high_cpa_terms[:50]
            ),
            "already_added_keywords": (
                already_added_keywords[:100]
            ),
            "already_excluded_terms": (
                already_excluded_terms[:100]
            ),
            "disclaimer": (
                "Les opportunités sont fondées sur "
                "les métriques et le statut de ciblage "
                "retournés par Google Ads. Vérifier "
                "l'intention, la valeur commerciale et "
                "le contexte avant toute modification."
            ),
        }

    except ValueError as error:
        return {
            "status": "FAILED",
            "automatic_action": False,
            "error": str(error),
        }

    except Exception as error:
        return {
            "status": "FAILED",
            "automatic_action": False,
            "error": str(error),
        }

# ============================================================ ============================================================ ============================================================ 

# ============================================================
# NEGATIVE KEYWORDS
# Lecture seule des mots-clés négatifs
# Niveau campagne et groupes d'annonces
# ============================================================

@app.get("/negative-keywords")
def negative_keywords(
    customer_id: str = Query(
        ...,
        description="ID du compte Google Ads",
    ),
    campaign_id: str = Query(
        ...,
        description="ID de la campagne Google Ads",
    ),
):
    try:
        customer_id = normalize_customer_id(
            customer_id
        )

        campaign_id = (
            campaign_id
            .replace("-", "")
            .strip()
        )

        if not campaign_id.isdigit():
            return {
                "status": "FAILED",
                "error": (
                    "campaign_id doit contenir "
                    "uniquement des chiffres."
                ),
            }

        client = get_google_ads_client()

        google_ads_service = client.get_service(
            "GoogleAdsService"
        )

        # ----------------------------------------------------
        # VÉRIFIER LA CAMPAGNE
        # ----------------------------------------------------

        campaign_query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type
            FROM campaign
            WHERE campaign.id = {campaign_id}
        """

        campaign_response = (
            google_ads_service.search(
                customer_id=customer_id,
                query=campaign_query,
            )
        )

        campaign_row = next(
            iter(campaign_response),
            None
        )

        if not campaign_row:
            return {
                "status": "FAILED",
                "error": "Campaign not found",
            }

        campaign_name = (
            campaign_row.campaign.name
        )

        campaign_type = enum_name(
            campaign_row
            .campaign
            .advertising_channel_type
        )

        # ----------------------------------------------------
        # MOTS-CLÉS NÉGATIFS AU NIVEAU CAMPAGNE
        # ----------------------------------------------------

        campaign_negative_query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign_criterion.criterion_id,
                campaign_criterion.status,
                campaign_criterion.negative,
                campaign_criterion.keyword.text,
                campaign_criterion.keyword.match_type,
                campaign_criterion.resource_name
            FROM campaign_criterion
            WHERE campaign.id = {campaign_id}
              AND campaign_criterion.type = 'KEYWORD'
              AND campaign_criterion.negative = TRUE
        """

        campaign_negative_response = (
            google_ads_service.search(
                customer_id=customer_id,
                query=campaign_negative_query,
            )
        )

        campaign_negative_keywords = []

        for row in campaign_negative_response:
            keyword_text = (
                row.campaign_criterion
                .keyword
                .text
            )

            match_type = enum_name(
                row.campaign_criterion
                .keyword
                .match_type
            )

            campaign_negative_keywords.append(
                {
                    "level": "CAMPAIGN",
                    "campaign_id": str(
                        row.campaign.id
                    ),
                    "campaign_name": (
                        row.campaign.name
                    ),
                    "ad_group_id": None,
                    "ad_group_name": None,
                    "criterion_id": str(
                        row.campaign_criterion
                        .criterion_id
                    ),
                    "keyword": keyword_text,
                    "normalized_keyword": (
                        keyword_text
                        .strip()
                        .casefold()
                    ),
                    "match_type": match_type,
                    "status": enum_name(
                        row.campaign_criterion
                        .status
                    ),
                    "negative": True,
                    "resource_name": (
                        row.campaign_criterion
                        .resource_name
                    ),
                }
            )

        # ----------------------------------------------------
        # MOTS-CLÉS NÉGATIFS AU NIVEAU GROUPE D'ANNONCES
        # ----------------------------------------------------

        ad_group_negative_query = f"""
            SELECT
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group_criterion.criterion_id,
                ad_group_criterion.status,
                ad_group_criterion.negative,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.resource_name
            FROM ad_group_criterion
            WHERE campaign.id = {campaign_id}
              AND ad_group_criterion.type = 'KEYWORD'
              AND ad_group_criterion.negative = TRUE
        """

        ad_group_negative_response = (
            google_ads_service.search(
                customer_id=customer_id,
                query=ad_group_negative_query,
            )
        )

        ad_group_negative_keywords = []

        for row in ad_group_negative_response:
            keyword_text = (
                row.ad_group_criterion
                .keyword
                .text
            )

            match_type = enum_name(
                row.ad_group_criterion
                .keyword
                .match_type
            )

            ad_group_negative_keywords.append(
                {
                    "level": "AD_GROUP",
                    "campaign_id": str(
                        row.campaign.id
                    ),
                    "campaign_name": (
                        row.campaign.name
                    ),
                    "ad_group_id": str(
                        row.ad_group.id
                    ),
                    "ad_group_name": (
                        row.ad_group.name
                    ),
                    "ad_group_status": enum_name(
                        row.ad_group.status
                    ),
                    "criterion_id": str(
                        row.ad_group_criterion
                        .criterion_id
                    ),
                    "keyword": keyword_text,
                    "normalized_keyword": (
                        keyword_text
                        .strip()
                        .casefold()
                    ),
                    "match_type": match_type,
                    "status": enum_name(
                        row.ad_group_criterion
                        .status
                    ),
                    "negative": True,
                    "resource_name": (
                        row.ad_group_criterion
                        .resource_name
                    ),
                }
            )

        # ----------------------------------------------------
        # INDEX POUR VÉRIFICATIONS RAPIDES
        # ----------------------------------------------------

        all_negative_keywords = (
            campaign_negative_keywords
            + ad_group_negative_keywords
        )

        unique_normalized_keywords = sorted(
            {
                item["normalized_keyword"]
                for item in all_negative_keywords
            }
        )

        keywords_by_match_type = {
            "EXACT": 0,
            "PHRASE": 0,
            "BROAD": 0,
            "OTHER": 0,
        }

        for item in all_negative_keywords:
            match_type = item["match_type"]

            if match_type in keywords_by_match_type:
                keywords_by_match_type[
                    match_type
                ] += 1

            else:
                keywords_by_match_type[
                    "OTHER"
                ] += 1

        campaign_negative_keywords.sort(
            key=lambda item: (
                item["keyword"].casefold(),
                item["match_type"],
            )
        )

        ad_group_negative_keywords.sort(
            key=lambda item: (
                (
                    item["ad_group_name"]
                    or ""
                ).casefold(),
                item["keyword"].casefold(),
                item["match_type"],
            )
        )

        return {
            "status": "SUCCESS",
            "mode": "READ_ONLY",
            "automatic_action": False,
            "customer_id": customer_id,
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "campaign_status": enum_name(
                campaign_row.campaign.status
            ),
            "campaign_type": campaign_type,
            "summary": {
                "total_negative_keywords": len(
                    all_negative_keywords
                ),
                "unique_negative_keywords": len(
                    unique_normalized_keywords
                ),
                "campaign_level": len(
                    campaign_negative_keywords
                ),
                "ad_group_level": len(
                    ad_group_negative_keywords
                ),
                "by_match_type": (
                    keywords_by_match_type
                ),
            },
            "campaign_negative_keywords": (
                campaign_negative_keywords
            ),
            "ad_group_negative_keywords": (
                ad_group_negative_keywords
            ),
            "all_negative_keywords": (
                all_negative_keywords
            ),
            "negative_keyword_index": (
                unique_normalized_keywords
            ),
            "scope_notice": (
                "Cette réponse contient les mots-clés "
                "négatifs ajoutés directement à la "
                "campagne et aux groupes d'annonces."
            ),
        }

    except Exception as error:
        return {
            "status": "FAILED",
            "automatic_action": False,
            "error": str(error),
        }
            
# ============================================================
# REMOVE NEGATIVE KEYWORD
# Suppression protégée par code de confirmation
# Utilise le resource_name exact du critère
# ============================================================

@app.post("/remove-negative-keyword")
def remove_negative_keyword(
    request: RemoveNegativeKeywordRequest
):
    try:
        # ----------------------------------------------------
        # NORMALISATION
        # ----------------------------------------------------

        customer_id = normalize_customer_id(
            request.customer_id
        )

        campaign_id = (
            request.campaign_id
            .replace("-", "")
            .strip()
        )

        level = (
            request.level
            .strip()
            .upper()
        )

        resource_name = (
            request.resource_name
            .strip()
        )

        # ----------------------------------------------------
        # VALIDATION DU CODE
        # ----------------------------------------------------

        expected_code = os.getenv(
            "CONFIRMATION_CODE"
        )

        if not expected_code:
            return {
                "status": "FAILED",
                "action": (
                    "REMOVE_NEGATIVE_KEYWORD"
                ),
                "error": (
                    "CONFIRMATION_CODE is not configured"
                ),
                "automatic_action": False,
            }

        if (
            request.confirmation_code
            != expected_code
        ):
            return {
                "status": "FAILED",
                "action": (
                    "REMOVE_NEGATIVE_KEYWORD"
                ),
                "error": (
                    "Confirmation code invalid"
                ),
                "automatic_action": False,
            }

        # ----------------------------------------------------
        # VALIDATION DES PARAMÈTRES
        # ----------------------------------------------------

        if not campaign_id.isdigit():
            return {
                "status": "FAILED",
                "action": (
                    "REMOVE_NEGATIVE_KEYWORD"
                ),
                "error": (
                    "campaign_id doit contenir "
                    "uniquement des chiffres."
                ),
                "automatic_action": False,
            }

        valid_levels = {
            "CAMPAIGN",
            "AD_GROUP",
        }

        if level not in valid_levels:
            return {
                "status": "FAILED",
                "action": (
                    "REMOVE_NEGATIVE_KEYWORD"
                ),
                "error": (
                    "level doit être CAMPAIGN "
                    "ou AD_GROUP."
                ),
                "automatic_action": False,
            }

        if not resource_name:
            return {
                "status": "FAILED",
                "action": (
                    "REMOVE_NEGATIVE_KEYWORD"
                ),
                "error": (
                    "resource_name est obligatoire."
                ),
                "automatic_action": False,
            }

        expected_customer_prefix = (
            f"customers/{customer_id}/"
        )

        if not resource_name.startswith(
            expected_customer_prefix
        ):
            return {
                "status": "FAILED",
                "action": (
                    "REMOVE_NEGATIVE_KEYWORD"
                ),
                "error": (
                    "Le resource_name n'appartient "
                    "pas au compte demandé."
                ),
                "automatic_action": False,
            }

        if (
            level == "CAMPAIGN"
            and "/campaignCriteria/"
            not in resource_name
        ):
            return {
                "status": "FAILED",
                "action": (
                    "REMOVE_NEGATIVE_KEYWORD"
                ),
                "error": (
                    "Le resource_name ne correspond "
                    "pas à un critère de campagne."
                ),
                "automatic_action": False,
            }

        if (
            level == "AD_GROUP"
            and "/adGroupCriteria/"
            not in resource_name
        ):
            return {
                "status": "FAILED",
                "action": (
                    "REMOVE_NEGATIVE_KEYWORD"
                ),
                "error": (
                    "Le resource_name ne correspond "
                    "pas à un critère de groupe "
                    "d'annonces."
                ),
                "automatic_action": False,
            }

        # ----------------------------------------------------
        # SERVICES GOOGLE ADS
        # ----------------------------------------------------

        client = get_google_ads_client()

        google_ads_service = client.get_service(
            "GoogleAdsService"
        )

        # ----------------------------------------------------
        # VÉRIFIER LA CAMPAGNE
        # ----------------------------------------------------

        campaign_query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type
            FROM campaign
            WHERE campaign.id = {campaign_id}
        """

        campaign_response = (
            google_ads_service.search(
                customer_id=customer_id,
                query=campaign_query,
            )
        )

        campaign_row = next(
            iter(campaign_response),
            None
        )

        if not campaign_row:
            return {
                "status": "FAILED",
                "action": (
                    "REMOVE_NEGATIVE_KEYWORD"
                ),
                "error": "Campaign not found",
                "automatic_action": False,
            }

        campaign_name = (
            campaign_row.campaign.name
        )

        campaign_type = enum_name(
            campaign_row
            .campaign
            .advertising_channel_type
        )

        keyword = None
        match_type = None
        criterion_id = None
        ad_group_id = None
        ad_group_name = None

        # ----------------------------------------------------
        # TROUVER LE CRITÈRE DE CAMPAGNE
        # ----------------------------------------------------

        if level == "CAMPAIGN":
            existing_query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign_criterion.criterion_id,
                    campaign_criterion.status,
                    campaign_criterion.negative,
                    campaign_criterion.keyword.text,
                    campaign_criterion.keyword.match_type,
                    campaign_criterion.resource_name
                FROM campaign_criterion
                WHERE campaign.id = {campaign_id}
                  AND campaign_criterion.type = 'KEYWORD'
                  AND campaign_criterion.negative = TRUE
            """

            existing_response = (
                google_ads_service.search(
                    customer_id=customer_id,
                    query=existing_query,
                )
            )

            matching_row = None

            for row in existing_response:
                if (
                    row.campaign_criterion
                    .resource_name
                    == resource_name
                ):
                    matching_row = row
                    break

            if not matching_row:
                return {
                    "status": "NO_CHANGE",
                    "action": (
                        "REMOVE_NEGATIVE_KEYWORD"
                    ),
                    "message": (
                        "Le mot-clé négatif demandé "
                        "n'existe plus au niveau campagne."
                    ),
                    "customer_id": customer_id,
                    "campaign_id": campaign_id,
                    "campaign_name": campaign_name,
                    "level": level,
                    "resource_name": (
                        resource_name
                    ),
                    "already_removed": True,
                    "automatic_action": False,
                }

            keyword = (
                matching_row
                .campaign_criterion
                .keyword
                .text
            )

            match_type = enum_name(
                matching_row
                .campaign_criterion
                .keyword
                .match_type
            )

            criterion_id = str(
                matching_row
                .campaign_criterion
                .criterion_id
            )

            # ------------------------------------------------
            # SUPPRESSION AU NIVEAU CAMPAGNE
            # ------------------------------------------------

            campaign_criterion_service = (
                client.get_service(
                    "CampaignCriterionService"
                )
            )

            operation = client.get_type(
                "CampaignCriterionOperation"
            )

            operation.remove = resource_name

            result = (
                campaign_criterion_service
                .mutate_campaign_criteria(
                    customer_id=customer_id,
                    operations=[operation],
                )
            )

            removed_resource_name = (
                result.results[0]
                .resource_name
            )

        # ----------------------------------------------------
        # TROUVER LE CRITÈRE DU GROUPE D'ANNONCES
        # ----------------------------------------------------

        else:
            existing_query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    ad_group.id,
                    ad_group.name,
                    ad_group.status,
                    ad_group_criterion.criterion_id,
                    ad_group_criterion.status,
                    ad_group_criterion.negative,
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    ad_group_criterion.resource_name
                FROM ad_group_criterion
                WHERE campaign.id = {campaign_id}
                  AND ad_group_criterion.type = 'KEYWORD'
                  AND ad_group_criterion.negative = TRUE
            """

            existing_response = (
                google_ads_service.search(
                    customer_id=customer_id,
                    query=existing_query,
                )
            )

            matching_row = None

            for row in existing_response:
                if (
                    row.ad_group_criterion
                    .resource_name
                    == resource_name
                ):
                    matching_row = row
                    break

            if not matching_row:
                return {
                    "status": "NO_CHANGE",
                    "action": (
                        "REMOVE_NEGATIVE_KEYWORD"
                    ),
                    "message": (
                        "Le mot-clé négatif demandé "
                        "n'existe plus au niveau du "
                        "groupe d'annonces."
                    ),
                    "customer_id": customer_id,
                    "campaign_id": campaign_id,
                    "campaign_name": campaign_name,
                    "level": level,
                    "resource_name": (
                        resource_name
                    ),
                    "already_removed": True,
                    "automatic_action": False,
                }

            keyword = (
                matching_row
                .ad_group_criterion
                .keyword
                .text
            )

            match_type = enum_name(
                matching_row
                .ad_group_criterion
                .keyword
                .match_type
            )

            criterion_id = str(
                matching_row
                .ad_group_criterion
                .criterion_id
            )

            ad_group_id = str(
                matching_row
                .ad_group
                .id
            )

            ad_group_name = (
                matching_row
                .ad_group
                .name
            )

            # ------------------------------------------------
            # SUPPRESSION AU NIVEAU GROUPE
            # ------------------------------------------------

            ad_group_criterion_service = (
                client.get_service(
                    "AdGroupCriterionService"
                )
            )

            operation = client.get_type(
                "AdGroupCriterionOperation"
            )

            operation.remove = resource_name

            result = (
                ad_group_criterion_service
                .mutate_ad_group_criteria(
                    customer_id=customer_id,
                    operations=[operation],
                )
            )

            removed_resource_name = (
                result.results[0]
                .resource_name
            )

        # ----------------------------------------------------
        # SUCCÈS
        # ----------------------------------------------------

        return {
            "status": "SUCCESS",
            "action": (
                "REMOVE_NEGATIVE_KEYWORD"
            ),
            "customer_id": customer_id,
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "campaign_type": campaign_type,
            "level": level,
            "ad_group_id": ad_group_id,
            "ad_group_name": ad_group_name,
            "criterion_id": criterion_id,
            "keyword": keyword,
            "match_type": match_type,
            "resource_name": (
                removed_resource_name
            ),
            "negative_keyword_removed": True,
            "automatic_action": False,
            "human_confirmation_validated": True,
        }

    except Exception as error:
        return {
            "status": "FAILED",
            "action": (
                "REMOVE_NEGATIVE_KEYWORD"
            ),
            "automatic_action": False,
            "error": str(error),
        }
# ============================================================
# ADD NEGATIVE KEYWORD
# Modification protégée par code de confirmation
# Niveau campagne ou groupe d'annonces
# ============================================================

@app.post("/add-negative-keyword")
def add_negative_keyword(
    request: AddNegativeKeywordRequest
):
    try:
        # ----------------------------------------------------
        # NORMALISATION DES PARAMÈTRES
        # ----------------------------------------------------

        customer_id = normalize_customer_id(
            request.customer_id
        )

        campaign_id = (
            request.campaign_id
            .replace("-", "")
            .strip()
        )

        keyword = request.keyword.strip()

        normalized_keyword = (
            normalize_keyword_text(
                keyword
            )
        )

        level = (
            request.level
            .strip()
            .upper()
        )

        match_type = (
            request.match_type
            .strip()
            .upper()
        )

        ad_group_id = None

        if request.ad_group_id:
            ad_group_id = (
                request.ad_group_id
                .replace("-", "")
                .strip()
            )

        # ----------------------------------------------------
        # VALIDATION DU CODE DE CONFIRMATION
        # ----------------------------------------------------

        expected_code = os.getenv(
            "CONFIRMATION_CODE"
        )

        if not expected_code:
            return {
                "status": "FAILED",
                "error": (
                    "CONFIRMATION_CODE is not configured"
                ),
                "automatic_action": False,
            }

        if (
            request.confirmation_code
            != expected_code
        ):
            return {
                "status": "FAILED",
                "error": (
                    "Confirmation code invalid"
                ),
                "automatic_action": False,
            }

        # ----------------------------------------------------
        # VALIDATION DES PARAMÈTRES
        # ----------------------------------------------------

        if not campaign_id.isdigit():
            return {
                "status": "FAILED",
                "error": (
                    "campaign_id doit contenir "
                    "uniquement des chiffres."
                ),
                "automatic_action": False,
            }

        if not keyword:
            return {
                "status": "FAILED",
                "error": (
                    "Le mot-clé négatif ne peut "
                    "pas être vide."
                ),
                "automatic_action": False,
            }

        if len(keyword) > 80:
            return {
                "status": "FAILED",
                "error": (
                    "Le mot-clé négatif dépasse "
                    "la longueur autorisée."
                ),
                "automatic_action": False,
            }

        valid_levels = {
            "CAMPAIGN",
            "AD_GROUP",
        }

        if level not in valid_levels:
            return {
                "status": "FAILED",
                "error": (
                    "level doit être CAMPAIGN "
                    "ou AD_GROUP."
                ),
                "automatic_action": False,
            }

        valid_match_types = {
            "EXACT",
            "PHRASE",
            "BROAD",
        }

        if match_type not in valid_match_types:
            return {
                "status": "FAILED",
                "error": (
                    "match_type doit être EXACT, "
                    "PHRASE ou BROAD."
                ),
                "automatic_action": False,
            }

        if level == "AD_GROUP":
            if not ad_group_id:
                return {
                    "status": "FAILED",
                    "error": (
                        "ad_group_id est obligatoire "
                        "lorsque level = AD_GROUP."
                    ),
                    "automatic_action": False,
                }

            if not ad_group_id.isdigit():
                return {
                    "status": "FAILED",
                    "error": (
                        "ad_group_id doit contenir "
                        "uniquement des chiffres."
                    ),
                    "automatic_action": False,
                }

        # ----------------------------------------------------
        # SERVICES GOOGLE ADS
        # ----------------------------------------------------

        client = get_google_ads_client()

        google_ads_service = client.get_service(
            "GoogleAdsService"
        )

        # ----------------------------------------------------
        # VÉRIFIER LA CAMPAGNE
        # ----------------------------------------------------

        campaign_query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type
            FROM campaign
            WHERE campaign.id = {campaign_id}
        """

        campaign_response = (
            google_ads_service.search(
                customer_id=customer_id,
                query=campaign_query,
            )
        )

        campaign_row = next(
            iter(campaign_response),
            None
        )

        if not campaign_row:
            return {
                "status": "FAILED",
                "error": "Campaign not found",
                "automatic_action": False,
            }

        campaign_name = (
            campaign_row.campaign.name
        )

        campaign_type = enum_name(
            campaign_row
            .campaign
            .advertising_channel_type
        )

        # ----------------------------------------------------
        # VÉRIFIER LE GROUPE D'ANNONCES
        # ----------------------------------------------------

        ad_group_name = None

        if level == "AD_GROUP":
            ad_group_query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    ad_group.id,
                    ad_group.name,
                    ad_group.status
                FROM ad_group
                WHERE campaign.id = {campaign_id}
                  AND ad_group.id = {ad_group_id}
            """

            ad_group_response = (
                google_ads_service.search(
                    customer_id=customer_id,
                    query=ad_group_query,
                )
            )

            ad_group_row = next(
                iter(ad_group_response),
                None
            )

            if not ad_group_row:
                return {
                    "status": "FAILED",
                    "error": (
                        "Ad group not found in "
                        "this campaign"
                    ),
                    "automatic_action": False,
                }

            ad_group_name = (
                ad_group_row.ad_group.name
            )

        # ----------------------------------------------------
        # VÉRIFIER LES DOUBLONS AU NIVEAU CAMPAGNE
        # ----------------------------------------------------

        if level == "CAMPAIGN":
            existing_query = f"""
                SELECT
                    campaign_criterion.criterion_id,
                    campaign_criterion.keyword.text,
                    campaign_criterion.keyword.match_type,
                    campaign_criterion.status,
                    campaign_criterion.resource_name
                FROM campaign_criterion
                WHERE campaign.id = {campaign_id}
                  AND campaign_criterion.type = 'KEYWORD'
                  AND campaign_criterion.negative = TRUE
            """

            existing_response = (
                google_ads_service.search(
                    customer_id=customer_id,
                    query=existing_query,
                )
            )

            for row in existing_response:
                existing_keyword = (
                    row.campaign_criterion
                    .keyword
                    .text
                )

                existing_match_type = enum_name(
                    row.campaign_criterion
                    .keyword
                    .match_type
                )

                if (
                    normalize_keyword_text(
                        existing_keyword
                    )
                    == normalized_keyword
                    and existing_match_type
                    == match_type
                ):
                    return {
                        "status": "NO_CHANGE",
                        "message": (
                            "Le mot-clé négatif existe "
                            "déjà au niveau campagne avec "
                            "le même type de correspondance."
                        ),
                        "customer_id": customer_id,
                        "campaign_id": campaign_id,
                        "campaign_name": campaign_name,
                        "level": level,
                        "ad_group_id": None,
                        "ad_group_name": None,
                        "keyword": keyword,
                        "match_type": match_type,
                        "already_exists": True,
                        "criterion_id": str(
                            row.campaign_criterion
                            .criterion_id
                        ),
                        "resource_name": (
                            row.campaign_criterion
                            .resource_name
                        ),
                        "automatic_action": False,
                    }

        # ----------------------------------------------------
        # VÉRIFIER LES DOUBLONS AU NIVEAU GROUPE
        # ----------------------------------------------------

        if level == "AD_GROUP":
            existing_query = f"""
                SELECT
                    ad_group.id,
                    ad_group.name,
                    ad_group_criterion.criterion_id,
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    ad_group_criterion.status,
                    ad_group_criterion.resource_name
                FROM ad_group_criterion
                WHERE campaign.id = {campaign_id}
                  AND ad_group.id = {ad_group_id}
                  AND ad_group_criterion.type = 'KEYWORD'
                  AND ad_group_criterion.negative = TRUE
            """

            existing_response = (
                google_ads_service.search(
                    customer_id=customer_id,
                    query=existing_query,
                )
            )

            for row in existing_response:
                existing_keyword = (
                    row.ad_group_criterion
                    .keyword
                    .text
                )

                existing_match_type = enum_name(
                    row.ad_group_criterion
                    .keyword
                    .match_type
                )

                if (
                    normalize_keyword_text(
                        existing_keyword
                    )
                    == normalized_keyword
                    and existing_match_type
                    == match_type
                ):
                    return {
                        "status": "NO_CHANGE",
                        "message": (
                            "Le mot-clé négatif existe "
                            "déjà dans ce groupe d'annonces "
                            "avec le même type de correspondance."
                        ),
                        "customer_id": customer_id,
                        "campaign_id": campaign_id,
                        "campaign_name": campaign_name,
                        "level": level,
                        "ad_group_id": ad_group_id,
                        "ad_group_name": ad_group_name,
                        "keyword": keyword,
                        "match_type": match_type,
                        "already_exists": True,
                        "criterion_id": str(
                            row.ad_group_criterion
                            .criterion_id
                        ),
                        "resource_name": (
                            row.ad_group_criterion
                            .resource_name
                        ),
                        "automatic_action": False,
                    }

        # ----------------------------------------------------
        # MAPPER LE TYPE DE CORRESPONDANCE
        # ----------------------------------------------------

        match_type_enum = {
            "EXACT": (
                client.enums
                .KeywordMatchTypeEnum
                .EXACT
            ),
            "PHRASE": (
                client.enums
                .KeywordMatchTypeEnum
                .PHRASE
            ),
            "BROAD": (
                client.enums
                .KeywordMatchTypeEnum
                .BROAD
            ),
        }[match_type]

        # ----------------------------------------------------
        # AJOUT AU NIVEAU CAMPAGNE
        # ----------------------------------------------------

        if level == "CAMPAIGN":
            campaign_criterion_service = (
                client.get_service(
                    "CampaignCriterionService"
                )
            )

            operation = client.get_type(
                "CampaignCriterionOperation"
            )

            criterion = operation.create

            criterion.campaign = (
                google_ads_service
                .campaign_path(
                    customer_id,
                    campaign_id,
                )
            )

            criterion.negative = True

            criterion.keyword.text = keyword

            criterion.keyword.match_type = (
                match_type_enum
            )

            result = (
                campaign_criterion_service
                .mutate_campaign_criteria(
                    customer_id=customer_id,
                    operations=[operation],
                )
            )

            resource_name = (
                result.results[0]
                .resource_name
            )

        # ----------------------------------------------------
        # AJOUT AU NIVEAU GROUPE D'ANNONCES
        # ----------------------------------------------------

        else:
            ad_group_criterion_service = (
                client.get_service(
                    "AdGroupCriterionService"
                )
            )

            operation = client.get_type(
                "AdGroupCriterionOperation"
            )

            criterion = operation.create

            criterion.ad_group = (
                google_ads_service
                .ad_group_path(
                    customer_id,
                    ad_group_id,
                )
            )

            criterion.negative = True

            criterion.keyword.text = keyword

            criterion.keyword.match_type = (
                match_type_enum
            )

            result = (
                ad_group_criterion_service
                .mutate_ad_group_criteria(
                    customer_id=customer_id,
                    operations=[operation],
                )
            )

            resource_name = (
                result.results[0]
                .resource_name
            )

        # ----------------------------------------------------
        # SUCCÈS
        # ----------------------------------------------------

        return {
            "status": "SUCCESS",
            "action": "ADD_NEGATIVE_KEYWORD",
            "customer_id": customer_id,
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "campaign_type": campaign_type,
            "level": level,
            "ad_group_id": ad_group_id,
            "ad_group_name": ad_group_name,
            "keyword": keyword,
            "normalized_keyword": (
                normalized_keyword
            ),
            "match_type": match_type,
            "negative": True,
            "already_exists": False,
            "resource_name": resource_name,
            "automatic_action": False,
            "human_confirmation_validated": True,
        }

    except Exception as error:
        return {
            "status": "FAILED",
            "action": "ADD_NEGATIVE_KEYWORD",
            "automatic_action": False,
            "error": str(error),
        }

# ============================================================
# ADD KEYWORD
# Ajout d'un mot-clé positif dans un groupe d'annonces
# Modification protégée par code de confirmation
# ============================================================

@app.post("/add-keyword")
def add_keyword(
    request: AddKeywordRequest
):
    try:
        # ----------------------------------------------------
        # NORMALISATION
        # ----------------------------------------------------

        customer_id = normalize_customer_id(
            request.customer_id
        )

        campaign_id = (
            request.campaign_id
            .replace("-", "")
            .strip()
        )

        ad_group_id = (
            request.ad_group_id
            .replace("-", "")
            .strip()
        )

        keyword = request.keyword.strip()

        normalized_keyword = (
            normalize_keyword_text(
                keyword
            )
        )

        match_type = (
            request.match_type
            .strip()
            .upper()
        )

        # ----------------------------------------------------
        # VALIDATION DU CODE DE CONFIRMATION
        # ----------------------------------------------------

        expected_code = os.getenv(
            "CONFIRMATION_CODE"
        )

        if not expected_code:
            return {
                "status": "FAILED",
                "action": "ADD_KEYWORD",
                "error": (
                    "CONFIRMATION_CODE is not configured"
                ),
                "automatic_action": False,
            }

        if (
            request.confirmation_code
            != expected_code
        ):
            return {
                "status": "FAILED",
                "action": "ADD_KEYWORD",
                "error": (
                    "Confirmation code invalid"
                ),
                "automatic_action": False,
            }

        # ----------------------------------------------------
        # VALIDATION DES PARAMÈTRES
        # ----------------------------------------------------

        if not campaign_id.isdigit():
            return {
                "status": "FAILED",
                "action": "ADD_KEYWORD",
                "error": (
                    "campaign_id doit contenir "
                    "uniquement des chiffres."
                ),
                "automatic_action": False,
            }

        if not ad_group_id.isdigit():
            return {
                "status": "FAILED",
                "action": "ADD_KEYWORD",
                "error": (
                    "ad_group_id doit contenir "
                    "uniquement des chiffres."
                ),
                "automatic_action": False,
            }

        if not keyword:
            return {
                "status": "FAILED",
                "action": "ADD_KEYWORD",
                "error": (
                    "Le mot-clé ne peut pas être vide."
                ),
                "automatic_action": False,
            }

        if len(keyword) > 80:
            return {
                "status": "FAILED",
                "action": "ADD_KEYWORD",
                "error": (
                    "Le mot-clé dépasse la longueur "
                    "autorisée."
                ),
                "automatic_action": False,
            }

        valid_match_types = {
            "EXACT",
            "PHRASE",
            "BROAD",
        }

        if match_type not in valid_match_types:
            return {
                "status": "FAILED",
                "action": "ADD_KEYWORD",
                "error": (
                    "match_type doit être EXACT, "
                    "PHRASE ou BROAD."
                ),
                "automatic_action": False,
            }

        # ----------------------------------------------------
        # SERVICES GOOGLE ADS
        # ----------------------------------------------------

        client = get_google_ads_client()

        google_ads_service = client.get_service(
            "GoogleAdsService"
        )

        # ----------------------------------------------------
        # VÉRIFIER LA CAMPAGNE
        # ----------------------------------------------------

        campaign_query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type
            FROM campaign
            WHERE campaign.id = {campaign_id}
        """

        campaign_response = (
            google_ads_service.search(
                customer_id=customer_id,
                query=campaign_query,
            )
        )

        campaign_row = next(
            iter(campaign_response),
            None
        )

        if not campaign_row:
            return {
                "status": "FAILED",
                "action": "ADD_KEYWORD",
                "error": "Campaign not found",
                "automatic_action": False,
            }

        campaign_name = (
            campaign_row.campaign.name
        )

        campaign_status = enum_name(
            campaign_row.campaign.status
        )

        campaign_type = enum_name(
            campaign_row
            .campaign
            .advertising_channel_type
        )

        # ----------------------------------------------------
        # VÉRIFIER LE GROUPE D'ANNONCES
        # ----------------------------------------------------

        ad_group_query = f"""
            SELECT
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.type,
                ad_group.resource_name
            FROM ad_group
            WHERE campaign.id = {campaign_id}
              AND ad_group.id = {ad_group_id}
        """

        ad_group_response = (
            google_ads_service.search(
                customer_id=customer_id,
                query=ad_group_query,
            )
        )

        ad_group_row = next(
            iter(ad_group_response),
            None
        )

        if not ad_group_row:
            return {
                "status": "FAILED",
                "action": "ADD_KEYWORD",
                "error": (
                    "Ad group not found in this campaign"
                ),
                "automatic_action": False,
            }

        ad_group_name = (
            ad_group_row.ad_group.name
        )

        ad_group_status = enum_name(
            ad_group_row.ad_group.status
        )

        # ----------------------------------------------------
        # VÉRIFIER LES MOTS-CLÉS POSITIFS EXISTANTS
        # ----------------------------------------------------

        existing_keyword_query = f"""
            SELECT
                campaign.id,
                ad_group.id,
                ad_group.name,
                ad_group_criterion.criterion_id,
                ad_group_criterion.status,
                ad_group_criterion.negative,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.resource_name
            FROM ad_group_criterion
            WHERE campaign.id = {campaign_id}
              AND ad_group.id = {ad_group_id}
              AND ad_group_criterion.type = 'KEYWORD'
              AND ad_group_criterion.negative = FALSE
        """

        existing_keyword_response = (
            google_ads_service.search(
                customer_id=customer_id,
                query=existing_keyword_query,
            )
        )

        for row in existing_keyword_response:
            existing_keyword = (
                row.ad_group_criterion
                .keyword
                .text
            )

            existing_match_type = enum_name(
                row.ad_group_criterion
                .keyword
                .match_type
            )

            if (
                normalize_keyword_text(
                    existing_keyword
                )
                == normalized_keyword
                and existing_match_type
                == match_type
            ):
                return {
                    "status": "NO_CHANGE",
                    "action": "ADD_KEYWORD",
                    "message": (
                        "Ce mot-clé existe déjà dans "
                        "le groupe d'annonces avec le "
                        "même type de correspondance."
                    ),
                    "customer_id": customer_id,
                    "campaign_id": campaign_id,
                    "campaign_name": campaign_name,
                    "ad_group_id": ad_group_id,
                    "ad_group_name": ad_group_name,
                    "keyword": keyword,
                    "match_type": match_type,
                    "keyword_status": enum_name(
                        row.ad_group_criterion
                        .status
                    ),
                    "criterion_id": str(
                        row.ad_group_criterion
                        .criterion_id
                    ),
                    "resource_name": (
                        row.ad_group_criterion
                        .resource_name
                    ),
                    "already_exists": True,
                    "automatic_action": False,
                }

        # ----------------------------------------------------
        # VÉRIFIER LES NÉGATIFS AU NIVEAU CAMPAGNE
        # ----------------------------------------------------

        campaign_negative_query = f"""
            SELECT
                campaign_criterion.criterion_id,
                campaign_criterion.keyword.text,
                campaign_criterion.keyword.match_type,
                campaign_criterion.resource_name
            FROM campaign_criterion
            WHERE campaign.id = {campaign_id}
              AND campaign_criterion.type = 'KEYWORD'
              AND campaign_criterion.negative = TRUE
        """

        campaign_negative_response = (
            google_ads_service.search(
                customer_id=customer_id,
                query=campaign_negative_query,
            )
        )

        campaign_conflicts = []

        for row in campaign_negative_response:
            negative_keyword = (
                row.campaign_criterion
                .keyword
                .text
            )

            negative_match_type = enum_name(
                row.campaign_criterion
                .keyword
                .match_type
            )

            if (
                normalize_keyword_text(
                    negative_keyword
                )
                == normalized_keyword
            ):
                campaign_conflicts.append(
                    {
                        "level": "CAMPAIGN",
                        "keyword": negative_keyword,
                        "match_type": (
                            negative_match_type
                        ),
                        "criterion_id": str(
                            row.campaign_criterion
                            .criterion_id
                        ),
                        "resource_name": (
                            row.campaign_criterion
                            .resource_name
                        ),
                    }
                )

        # ----------------------------------------------------
        # VÉRIFIER LES NÉGATIFS AU NIVEAU GROUPE
        # ----------------------------------------------------

        ad_group_negative_query = f"""
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.resource_name
            FROM ad_group_criterion
            WHERE campaign.id = {campaign_id}
              AND ad_group.id = {ad_group_id}
              AND ad_group_criterion.type = 'KEYWORD'
              AND ad_group_criterion.negative = TRUE
        """

        ad_group_negative_response = (
            google_ads_service.search(
                customer_id=customer_id,
                query=ad_group_negative_query,
            )
        )

        ad_group_conflicts = []

        for row in ad_group_negative_response:
            negative_keyword = (
                row.ad_group_criterion
                .keyword
                .text
            )

            negative_match_type = enum_name(
                row.ad_group_criterion
                .keyword
                .match_type
            )

            if (
                normalize_keyword_text(
                    negative_keyword
                )
                == normalized_keyword
            ):
                ad_group_conflicts.append(
                    {
                        "level": "AD_GROUP",
                        "keyword": negative_keyword,
                        "match_type": (
                            negative_match_type
                        ),
                        "criterion_id": str(
                            row.ad_group_criterion
                            .criterion_id
                        ),
                        "resource_name": (
                            row.ad_group_criterion
                            .resource_name
                        ),
                    }
                )

        negative_conflicts = (
            campaign_conflicts
            + ad_group_conflicts
        )

        if negative_conflicts:
            return {
                "status": "BLOCKED",
                "action": "ADD_KEYWORD",
                "message": (
                    "Ce terme correspond déjà à un "
                    "mot-clé négatif. Retirer ou réviser "
                    "l'exclusion avant de créer le "
                    "mot-clé positif."
                ),
                "customer_id": customer_id,
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "ad_group_id": ad_group_id,
                "ad_group_name": ad_group_name,
                "keyword": keyword,
                "match_type": match_type,
                "negative_conflicts": (
                    negative_conflicts
                ),
                "automatic_action": False,
            }

        # ----------------------------------------------------
        # MAPPER LE TYPE DE CORRESPONDANCE
        # ----------------------------------------------------

        match_type_enum = {
            "EXACT": (
                client.enums
                .KeywordMatchTypeEnum
                .EXACT
            ),
            "PHRASE": (
                client.enums
                .KeywordMatchTypeEnum
                .PHRASE
            ),
            "BROAD": (
                client.enums
                .KeywordMatchTypeEnum
                .BROAD
            ),
        }[match_type]

        # ----------------------------------------------------
        # CRÉER LE MOT-CLÉ
        # ----------------------------------------------------

        ad_group_criterion_service = (
            client.get_service(
                "AdGroupCriterionService"
            )
        )

        operation = client.get_type(
            "AdGroupCriterionOperation"
        )

        criterion = operation.create

        criterion.ad_group = (
            ad_group_row.ad_group.resource_name
        )

        criterion.status = (
            client.enums
            .AdGroupCriterionStatusEnum
            .ENABLED
        )

        criterion.negative = False

        criterion.keyword.text = keyword

        criterion.keyword.match_type = (
            match_type_enum
        )

        result = (
            ad_group_criterion_service
            .mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=[operation],
            )
        )

        resource_name = (
            result.results[0]
            .resource_name
        )

        # ----------------------------------------------------
        # SUCCÈS
        # ----------------------------------------------------

        return {
            "status": "SUCCESS",
            "action": "ADD_KEYWORD",
            "customer_id": customer_id,
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "campaign_status": campaign_status,
            "campaign_type": campaign_type,
            "ad_group_id": ad_group_id,
            "ad_group_name": ad_group_name,
            "ad_group_status": (
                ad_group_status
            ),
            "keyword": keyword,
            "normalized_keyword": (
                normalized_keyword
            ),
            "match_type": match_type,
            "keyword_status": "ENABLED",
            "negative": False,
            "already_exists": False,
            "resource_name": resource_name,
            "automatic_action": False,
            "human_confirmation_validated": True,
            "delivery_notice": (
                "Le mot-clé est activé, mais sa "
                "diffusion dépend aussi du statut "
                "de la campagne, du groupe "
                "d'annonces et de l'admissibilité "
                "Google Ads."
            ),
        }

    except Exception as error:
        return {
            "status": "FAILED",
            "action": "ADD_KEYWORD",
            "automatic_action": False,
            "error": str(error),
        }
# ============================================================
# TERMES DE RECHERCHE
# ============================================================

@app.get("/search-terms-old")
def search_terms(
customer_id: str
):
    try:
        client = get_google_ads_client()

        customer_id = normalize_customer_id(
                customer_id
        )
        

        query = """
            SELECT
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                search_term_view.search_term,
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.cost_micros,
                metrics.conversions
            FROM search_term_view
            WHERE segments.date DURING LAST_30_DAYS
        """

        response = execute_query(
    client,
    customer_id,
    query
)

        data = []

        for row in response:
            cost = row.metrics.cost_micros / 1_000_000
            conversions = safe_float(row.metrics.conversions)

            cpa = (
                round(cost / conversions, 2)
                if conversions > 0
                else None
            )

            data.append(
                {
                    "campaign_id": str(row.campaign.id),
                    "campaign": row.campaign.name,
                    "ad_group_id": str(row.ad_group.id),
                    "ad_group": row.ad_group.name,
                    "search_term": (
                        row.search_term_view.search_term
                    ),
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "ctr": round(
                        safe_float(row.metrics.ctr) * 100,
                        2,
                    ),
                    "cost": round(cost, 2),
                    "conversions": round(conversions, 2),
                    "cpa": cpa,
                }
            )

        return data

    except Exception as error:
        return {"error": str(error)}

# ============================================================
# OPTIMIZATION OPPORTUNITIES
# Analyse à la demande d'une campagne précise
# AUCUNE modification automatique
# ============================================================

@app.get("/optimization-opportunities")
def optimization_opportunities(
    customer_id: str = Query(..., description="ID du compte Google Ads"),
    campaign_id: str = Query(..., description="ID Google Ads de la campagne à analyser"),
    period: str = Query(
        default="LAST_30_DAYS",
        description="Période Google Ads prédéfinie. LAST_30_DAYS par défaut.",
    ),
    start_date: Optional[str] = Query(
        default=None,
        description="Date de début personnalisée au format YYYY-MM-DD.",
    ),
    end_date: Optional[str] = Query(
        default=None,
        description="Date de fin personnalisée au format YYYY-MM-DD.",
    ),
):
    try:
        customer_id = normalize_customer_id(customer_id)
        campaign_id = campaign_id.replace("-", "").strip()

        if not campaign_id.isdigit():
            return {
                "status": "FAILED",
                "campaign_id": campaign_id,
                "automatic_action": False,
                "error": "campaign_id doit contenir uniquement des chiffres.",
            }

        date_configuration = build_date_filter(
            period=period,
            start_date=start_date,
            end_date=end_date,
        )
        date_filter = date_configuration["filter"]
        date_range = {
            "mode": date_configuration["mode"],
            "period": date_configuration["period"],
            "start_date": date_configuration["start_date"],
            "end_date": date_configuration["end_date"],
        }

        client = get_google_ads_client()
        opportunities: List[Dict[str, Any]] = []
        audit_errors: List[Dict[str, str]] = []
        audit_coverage: Dict[str, str] = {}
        campaign_summary: Dict[str, Any] = {
            "campaign_id": campaign_id,
            "date_range": date_range,
        }

        # ----------------------------------------------------
        # 1. PERFORMANCE, CPA, ROAS, IMPRESSION SHARE, ENCHÈRES
        # ----------------------------------------------------
        try:
            performance_query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    campaign.advertising_channel_type,
                    campaign.bidding_strategy_type,
                    campaign_budget.amount_micros,
                    campaign_budget.status,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.ctr,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.search_impression_share,
                    metrics.search_budget_lost_impression_share,
                    metrics.search_rank_lost_impression_share
                FROM campaign
                WHERE campaign.id = {campaign_id}
                  AND {date_filter}
            """
            rows = execute_query(client, customer_id, performance_query)

            if not rows:
                return {
                    "status": "NO_DATA",
                    "campaign_id": campaign_id,
                    "customer_id": customer_id,
                    "date_range": date_range,
                    "message": "Aucune donnée n'a été retournée pour la période demandée.",
                    "automatic_action": False,
                }

            row = rows[0]
            cost = row.metrics.cost_micros / 1_000_000
            conversions = safe_float(row.metrics.conversions)
            conversion_value = safe_float(row.metrics.conversions_value)
            cpa = round(cost / conversions, 2) if conversions > 0 else None
            roas = round(conversion_value / cost, 2) if cost > 0 else None
            ctr = round(safe_float(row.metrics.ctr) * 100, 2)
            impression_share = safe_float(row.metrics.search_impression_share)
            lost_budget = safe_float(row.metrics.search_budget_lost_impression_share)
            lost_rank = safe_float(row.metrics.search_rank_lost_impression_share)
            daily_budget = row.campaign_budget.amount_micros / 1_000_000
            bidding_strategy = enum_name(row.campaign.bidding_strategy_type)

            campaign_summary.update({
                "campaign_name": row.campaign.name,
                "status": enum_name(row.campaign.status),
                "channel_type": enum_name(row.campaign.advertising_channel_type),
                "bidding_strategy": bidding_strategy,
                "daily_budget": round(daily_budget, 2),
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "ctr_percent": ctr,
                "cost": round(cost, 2),
                "conversions": round(conversions, 2),
                "conversion_value": round(conversion_value, 2),
                "cpa": cpa,
                "roas": roas,
                "search_impression_share_percent": (
                    round(impression_share * 100, 2) if impression_share > 0 else None
                ),
                "lost_budget_share_percent": (
                    round(lost_budget * 100, 2) if lost_budget > 0 else 0
                ),
                "lost_rank_share_percent": (
                    round(lost_rank * 100, 2) if lost_rank > 0 else 0
                ),
            })
            audit_coverage["campaign_performance"] = "SUCCESS"

            non_smart_strategies = {
                "MANUAL_CPC", "MANUAL_CPM", "MANUAL_CPV", "COMMISSION"
            }
            if conversions >= 30 and bidding_strategy in non_smart_strategies:
                add_opportunity(
                    opportunities,
                    "MEDIUM",
                    "BIDDING_STRATEGY",
                    "Volume suffisant pour évaluer une stratégie intelligente",
                    (
                        f"La campagne a généré {round(conversions, 2)} conversions "
                        f"durant la période analysée et utilise {bidding_strategy}."
                    ),
                    (
                        "Évaluer Maximiser les conversions ou CPA cible. Vérifier "
                        "d'abord la qualité du suivi des conversions et la stabilité du CPA."
                    ),
                    {
                        "conversions_analyzed_period": round(conversions, 2),
                        "current_strategy": bidding_strategy,
                        "observed_cpa": cpa,
                    },
                )

            if lost_budget >= 0.20:
                if conversions >= 10 and roas is not None and roas >= 2:
                    add_opportunity(
                        opportunities,
                        "HIGH",
                        "IMPRESSION_SHARE_BUDGET",
                        "Part d'impressions perdue à cause du budget",
                        (
                            f"La campagne perd environ {round(lost_budget * 100, 2)} % "
                            "des impressions à cause du budget."
                        ),
                        (
                            "La campagne produit des conversions et un ROAS positif. "
                            "Évaluer une augmentation progressive du budget après validation."
                        ),
                        {
                            "lost_budget_share_percent": round(lost_budget * 100, 2),
                            "conversions": round(conversions, 2),
                            "cpa": cpa,
                            "roas": roas,
                            "current_daily_budget": round(daily_budget, 2),
                        },
                    )
                else:
                    add_opportunity(
                        opportunities,
                        "MEDIUM",
                        "IMPRESSION_SHARE_BUDGET",
                        "Part d'impressions perdue à cause du budget",
                        (
                            f"La campagne perd environ {round(lost_budget * 100, 2)} % "
                            "des impressions à cause du budget."
                        ),
                        (
                            "Ne pas augmenter automatiquement le budget. Examiner d'abord "
                            "le CPA, le ROAS et la qualité des conversions."
                        ),
                        {
                            "lost_budget_share_percent": round(lost_budget * 100, 2),
                            "conversions": round(conversions, 2),
                            "cpa": cpa,
                            "roas": roas,
                        },
                    )

            if lost_rank >= 0.20:
                add_opportunity(
                    opportunities,
                    "HIGH",
                    "IMPRESSION_SHARE_RANK",
                    "Part d'impressions perdue à cause du classement",
                    (
                        f"La campagne perd environ {round(lost_rank * 100, 2)} % "
                        "des impressions à cause du classement."
                    ),
                    (
                        "Analyser le Quality Score, la pertinence des annonces, le CTR "
                        "attendu, l'expérience de page de destination et les enchères."
                    ),
                    {
                        "lost_rank_share_percent": round(lost_rank * 100, 2),
                        "ctr_percent": ctr,
                        "cpa": cpa,
                    },
                )
        except Exception as error:
            audit_coverage["campaign_performance"] = "FAILED"
            audit_errors.append({"audit": "campaign_performance", "error": str(error)})

        # ----------------------------------------------------
        # 2. ANALYSE COMPARATIVE DES GROUPES D'ANNONCES
        # ----------------------------------------------------
        try:
            ad_group_query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    ad_group.id,
                    ad_group.name,
                    ad_group.status,
                    ad_group.type,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.conversions_from_interactions_rate
                FROM ad_group
                WHERE campaign.id = {campaign_id}
                  AND {date_filter}
                ORDER BY metrics.cost_micros DESC
            """
            ad_group_rows = execute_query(client, customer_id, ad_group_query)
            ad_group_performance = []

            for row in ad_group_rows:
                item_cost = row.metrics.cost_micros / 1_000_000
                item_conversions = safe_float(row.metrics.conversions)
                item_value = safe_float(row.metrics.conversions_value)
                item_ctr = safe_float(row.metrics.ctr) * 100
                item_conversion_rate = (
                    safe_float(row.metrics.conversions_from_interactions_rate) * 100
                )
                item_average_cpc = row.metrics.average_cpc / 1_000_000
                item_cpa = item_cost / item_conversions if item_conversions > 0 else None
                item_roas = item_value / item_cost if item_cost > 0 else None

                ad_group_performance.append({
                    "ad_group_id": str(row.ad_group.id),
                    "ad_group_name": row.ad_group.name,
                    "status": enum_name(row.ad_group.status),
                    "type": enum_name(row.ad_group.type),
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "ctr_percent": round(item_ctr, 2),
                    "average_cpc": round(item_average_cpc, 2),
                    "cost": round(item_cost, 2),
                    "conversions": round(item_conversions, 2),
                    "conversion_rate_percent": round(item_conversion_rate, 2),
                    "conversion_value": round(item_value, 2),
                    "cpa": round(item_cpa, 2) if item_cpa is not None else None,
                    "roas": round(item_roas, 2) if item_roas is not None else None,
                })

            eligible = [x for x in ad_group_performance if x["clicks"] >= 5]
            with_conversions = [x for x in eligible if x["conversions"] > 0]
            without_conversions = [
                x for x in eligible if x["cost"] >= 10 and x["conversions"] == 0
            ]

            best_by_cpa = min(with_conversions, key=lambda x: x["cpa"]) if with_conversions else None
            worst_by_cpa = max(with_conversions, key=lambda x: x["cpa"]) if with_conversions else None
            best_by_conversions = (
                max(with_conversions, key=lambda x: x["conversions"])
                if with_conversions else None
            )
            with_roas = [x for x in with_conversions if x["roas"] is not None]
            best_by_roas = max(with_roas, key=lambda x: x["roas"]) if with_roas else None

            campaign_summary["ad_group_analysis"] = {
                "performance": ad_group_performance,
                "comparison": {
                    "total_ad_groups": len(ad_group_performance),
                    "groups_with_sufficient_data": len(eligible),
                    "best_by_cpa": best_by_cpa,
                    "worst_by_cpa": worst_by_cpa,
                    "best_by_roas": best_by_roas,
                    "best_by_conversion_volume": best_by_conversions,
                    "groups_spending_without_conversions": without_conversions,
                },
            }

            if without_conversions:
                add_opportunity(
                    opportunities,
                    "HIGH",
                    "AD_GROUP_NO_CONVERSIONS",
                    "Groupes d'annonces avec dépense sans conversion",
                    (
                        f"{len(without_conversions)} groupe(s) d'annonces ont dépensé "
                        "au moins 10 $ avec un minimum de 5 clics sans conversion."
                    ),
                    (
                        "Examiner les mots-clés, termes de recherche, annonces et pages "
                        "de destination. Ne pas les mettre en pause automatiquement."
                    ),
                    {"ad_groups": without_conversions},
                )

            if (
                best_by_cpa is not None
                and worst_by_cpa is not None
                and best_by_cpa["ad_group_id"] != worst_by_cpa["ad_group_id"]
                and worst_by_cpa["cpa"] >= best_by_cpa["cpa"] * 1.5
            ):
                add_opportunity(
                    opportunities,
                    "MEDIUM",
                    "AD_GROUP_CPA_GAP",
                    "Écart important de CPA entre les groupes d'annonces",
                    (
                        f"Le groupe {best_by_cpa['ad_group_name']} obtient un CPA de "
                        f"{best_by_cpa['cpa']}, tandis que {worst_by_cpa['ad_group_name']} "
                        f"obtient un CPA de {worst_by_cpa['cpa']}."
                    ),
                    (
                        "Comparer les intentions de recherche, les mots-clés, les annonces "
                        "et les pages. Évaluer une réallocation seulement après validation."
                    ),
                    {"best_ad_group": best_by_cpa, "weakest_ad_group": worst_by_cpa},
                )

            audit_coverage["ad_group_comparison"] = "SUCCESS"
        except Exception as error:
            audit_coverage["ad_group_comparison"] = "FAILED"
            audit_errors.append({"audit": "ad_group_comparison", "error": str(error)})

        # ----------------------------------------------------
        # 3. QUALITY SCORE ET TYPES DE CORRESPONDANCE
        # ----------------------------------------------------
        try:
            keyword_query = f"""
                SELECT
                    campaign.id,
                    ad_group.id,
                    ad_group.name,
                    ad_group_criterion.criterion_id,
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    ad_group_criterion.quality_info.quality_score,
                    ad_group_criterion.quality_info.creative_quality_score,
                    ad_group_criterion.quality_info.post_click_quality_score,
                    ad_group_criterion.quality_info.search_predicted_ctr,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions
                FROM keyword_view
                WHERE campaign.id = {campaign_id}
                  AND {date_filter}
            """
            keyword_rows = execute_query(client, customer_id, keyword_query)
            low_quality_keywords = []
            broad_waste_keywords = []

            for row in keyword_rows:
                keyword = row.ad_group_criterion.keyword.text
                match_type = enum_name(row.ad_group_criterion.keyword.match_type)
                quality_score = row.ad_group_criterion.quality_info.quality_score
                ad_relevance = enum_name(
                    row.ad_group_criterion.quality_info.creative_quality_score
                )
                landing_page = enum_name(
                    row.ad_group_criterion.quality_info.post_click_quality_score
                )
                expected_ctr = enum_name(
                    row.ad_group_criterion.quality_info.search_predicted_ctr
                )
                item_cost = row.metrics.cost_micros / 1_000_000
                item_conversions = safe_float(row.metrics.conversions)

                if 0 < quality_score <= 5:
                    low_quality_keywords.append({
                        "ad_group": row.ad_group.name,
                        "keyword": keyword,
                        "quality_score": quality_score,
                        "ad_relevance": ad_relevance,
                        "expected_ctr": expected_ctr,
                        "landing_page_experience": landing_page,
                        "impressions": row.metrics.impressions,
                        "clicks": row.metrics.clicks,
                        "cost": round(item_cost, 2),
                        "conversions": round(item_conversions, 2),
                    })

                if (
                    match_type == "BROAD"
                    and row.metrics.clicks >= 5
                    and item_conversions == 0
                    and item_cost >= 10
                ):
                    broad_waste_keywords.append({
                        "ad_group": row.ad_group.name,
                        "keyword": keyword,
                        "match_type": match_type,
                        "clicks": row.metrics.clicks,
                        "cost": round(item_cost, 2),
                        "conversions": 0,
                    })

            low_quality_keywords.sort(key=lambda x: (x["quality_score"], -x["cost"]))
            broad_waste_keywords.sort(key=lambda x: x["cost"], reverse=True)

            if low_quality_keywords:
                add_opportunity(
                    opportunities,
                    "HIGH",
                    "QUALITY_SCORE",
                    "Mots-clés avec un faible Quality Score",
                    f"{len(low_quality_keywords)} mot(s)-clé(s) ont un Quality Score de 5 ou moins.",
                    (
                        "Vérifier la pertinence de l'annonce, le CTR attendu et "
                        "l'expérience sur la page de destination."
                    ),
                    {"keywords": low_quality_keywords[:25]},
                )

            if broad_waste_keywords:
                add_opportunity(
                    opportunities,
                    "HIGH",
                    "MATCH_TYPE",
                    "Requêtes larges avec dépense sans conversion",
                    (
                        f"{len(broad_waste_keywords)} mot(s)-clé(s) larges ont au moins "
                        "5 clics, 10 $ de coût et aucune conversion."
                    ),
                    (
                        "Examiner les termes de recherche. Évaluer Phrase, Exact ou des "
                        "négatifs. Ne pas modifier automatiquement la correspondance."
                    ),
                    {"keywords": broad_waste_keywords[:25]},
                )

            audit_coverage["keyword_quality"] = "SUCCESS"
        except Exception as error:
            audit_coverage["keyword_quality"] = "FAILED"
            audit_errors.append({"audit": "keyword_quality", "error": str(error)})

        # ----------------------------------------------------
        # 4. PERFORMANCE DÉTAILLÉE DES MOTS-CLÉS
        # ----------------------------------------------------

        try:
            keyword_performance_query = f"""
                SELECT
                    campaign.id,
                    ad_group.id,
                    ad_group.name,
                    ad_group_criterion.criterion_id,
                    ad_group_criterion.status,
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.conversions_from_interactions_rate
                FROM keyword_view
                WHERE campaign.id = {campaign_id}
                  AND ad_group_criterion.status != 'REMOVED'
                  AND {date_filter}
                ORDER BY metrics.cost_micros DESC
            """

            keyword_performance_rows = (
                execute_query(
                    client,
                    customer_id,
                    keyword_performance_query,
                )
            )

            keyword_performance = []

            for row in keyword_performance_rows:
                keyword_cost = (
                    row.metrics.cost_micros
                    / 1_000_000
                )

                keyword_conversions = safe_float(
                    row.metrics.conversions
                )

                keyword_value = safe_float(
                    row.metrics.conversions_value
                )

                keyword_ctr = (
                    safe_float(
                        row.metrics.ctr
                    )
                    * 100
                )

                keyword_average_cpc = (
                    row.metrics.average_cpc
                    / 1_000_000
                )

                keyword_conversion_rate = (
                    safe_float(
                        row.metrics
                        .conversions_from_interactions_rate
                    )
                    * 100
                )

                keyword_cpa = (
                    keyword_cost
                    / keyword_conversions
                    if keyword_conversions > 0
                    else None
                )

                keyword_roas = (
                    keyword_value
                    / keyword_cost
                    if keyword_cost > 0
                    else None
                )

                keyword_performance.append(
                    {
                        "ad_group_id": str(
                            row.ad_group.id
                        ),
                        "ad_group_name": (
                            row.ad_group.name
                        ),
                        "criterion_id": str(
                            row.ad_group_criterion
                            .criterion_id
                        ),
                        "status": enum_name(
                            row.ad_group_criterion
                            .status
                        ),
                        "keyword": (
                            row.ad_group_criterion
                            .keyword
                            .text
                        ),
                        "match_type": enum_name(
                            row.ad_group_criterion
                            .keyword
                            .match_type
                        ),
                        "impressions": (
                            row.metrics.impressions
                        ),
                        "clicks": (
                            row.metrics.clicks
                        ),
                        "ctr_percent": round(
                            keyword_ctr,
                            2,
                        ),
                        "average_cpc": round(
                            keyword_average_cpc,
                            2,
                        ),
                        "cost": round(
                            keyword_cost,
                            2,
                        ),
                        "conversions": round(
                            keyword_conversions,
                            2,
                        ),
                        "conversion_rate_percent": (
                            round(
                                keyword_conversion_rate,
                                2,
                            )
                        ),
                        "conversion_value": round(
                            keyword_value,
                            2,
                        ),
                        "cpa": (
                            round(
                                keyword_cpa,
                                2,
                            )
                            if keyword_cpa
                            is not None
                            else None
                        ),
                        "roas": (
                            round(
                                keyword_roas,
                                2,
                            )
                            if keyword_roas
                            is not None
                            else None
                        ),
                    }
                )

            eligible_keywords = [
                item
                for item
                in keyword_performance
                if item["clicks"] >= 5
            ]

            converting_keywords = [
                item
                for item
                in eligible_keywords
                if item["conversions"] > 0
            ]

            keywords_without_conversions = [
                item
                for item
                in eligible_keywords
                if (
                    item["cost"] >= 10
                    and item["conversions"] == 0
                )
            ]

            low_ctr_keywords = [
                item
                for item
                in keyword_performance
                if (
                    item["impressions"] >= 100
                    and item["ctr_percent"] < 2
                )
            ]

            expensive_keywords = [
                item
                for item
                in converting_keywords
                if (
                    cpa is not None
                    and item["cpa"] is not None
                    and item["cpa"] >= cpa * 1.5
                )
            ]

            best_keyword_by_cpa = None
            worst_keyword_by_cpa = None
            best_keyword_by_roas = None
            best_keyword_by_conversions = None

            if converting_keywords:
                best_keyword_by_cpa = min(
                    converting_keywords,
                    key=lambda item: (
                        item["cpa"]
                    ),
                )

                worst_keyword_by_cpa = max(
                    converting_keywords,
                    key=lambda item: (
                        item["cpa"]
                    ),
                )

                best_keyword_by_conversions = max(
                    converting_keywords,
                    key=lambda item: (
                        item["conversions"]
                    ),
                )

                keywords_with_roas = [
                    item
                    for item
                    in converting_keywords
                    if item["roas"] is not None
                ]

                if keywords_with_roas:
                    best_keyword_by_roas = max(
                        keywords_with_roas,
                        key=lambda item: (
                            item["roas"]
                        ),
                    )

            campaign_summary[
                "keyword_performance_analysis"
            ] = {
                "keywords_analyzed": len(
                    keyword_performance
                ),
                "keywords_with_sufficient_data": (
                    len(
                        eligible_keywords
                    )
                ),
                "best_by_cpa": (
                    best_keyword_by_cpa
                ),
                "worst_by_cpa": (
                    worst_keyword_by_cpa
                ),
                "best_by_roas": (
                    best_keyword_by_roas
                ),
                "best_by_conversion_volume": (
                    best_keyword_by_conversions
                ),
                "keywords_spending_without_conversions": (
                    keywords_without_conversions[:25]
                ),
                "keywords_above_campaign_cpa": (
                    expensive_keywords[:25]
                ),
                "low_ctr_keywords": (
                    low_ctr_keywords[:25]
                ),
                "performance": (
                    keyword_performance[:100]
                ),
            }

            if keywords_without_conversions:
                add_opportunity(
                    opportunities,
                    "HIGH",
                    "KEYWORD_PERFORMANCE",
                    (
                        "Mots-clés avec dépense "
                        "sans conversion"
                    ),
                    (
                        f"{len(keywords_without_conversions)} "
                        f"mot(s)-clé(s) ont au moins "
                        f"5 clics et 10 $ de coût "
                        f"sans conversion."
                    ),
                    (
                        "Analyser les termes de recherche, "
                        "le type de correspondance, "
                        "l'annonce et la page de destination. "
                        "Ne pas suspendre automatiquement "
                        "ces mots-clés."
                    ),
                    {
                        "keywords": (
                            keywords_without_conversions[
                                :25
                            ]
                        ),
                    },
                )

            if expensive_keywords:
                add_opportunity(
                    opportunities,
                    "MEDIUM",
                    "KEYWORD_HIGH_CPA",
                    (
                        "Mots-clés avec un CPA "
                        "supérieur à la campagne"
                    ),
                    (
                        f"{len(expensive_keywords)} "
                        f"mot(s)-clé(s) ont un CPA "
                        f"d'au moins 1,5 fois le CPA "
                        f"de la campagne."
                    ),
                    (
                        "Comparer l'intention, le type "
                        "de correspondance, le Quality "
                        "Score, les termes de recherche "
                        "et la page de destination."
                    ),
                    {
                        "campaign_cpa": cpa,
                        "keywords": (
                            expensive_keywords[:25]
                        ),
                    },
                )

            if low_ctr_keywords:
                add_opportunity(
                    opportunities,
                    "MEDIUM",
                    "KEYWORD_LOW_CTR",
                    (
                        "Mots-clés avec un CTR faible"
                    ),
                    (
                        f"{len(low_ctr_keywords)} "
                        f"mot(s)-clé(s) ont au moins "
                        f"100 impressions et un CTR "
                        f"inférieur à 2 %."
                    ),
                    (
                        "Vérifier la pertinence du "
                        "mot-clé, le type de "
                        "correspondance, l'annonce "
                        "associée et l'intention de "
                        "recherche."
                    ),
                    {
                        "keywords": (
                            low_ctr_keywords[:25]
                        ),
                    },
                )

            audit_coverage[
                "keyword_performance"
            ] = "SUCCESS"

        except Exception as error:
            audit_coverage[
                "keyword_performance"
            ] = "FAILED"

            audit_errors.append(
                {
                    "audit": (
                        "keyword_performance"
                    ),
                    "error": str(error),
                }
            )


        # ----------------------------------------------------
        # 5. PERFORMANCE DES ANNONCES
        # ----------------------------------------------------

        try:
            ad_performance_query = f"""
                SELECT
                    campaign.id,
                    ad_group.id,
                    ad_group.name,
                    ad_group_ad.ad.id,
                    ad_group_ad.status,
                    ad_group_ad.ad.type,
                    ad_group_ad.ad_strength,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.conversions_from_interactions_rate
                FROM ad_group_ad
                WHERE campaign.id = {campaign_id}
                  AND ad_group_ad.status != 'REMOVED'
                  AND {date_filter}
                ORDER BY metrics.cost_micros DESC
            """

            ad_rows = execute_query(
                client,
                customer_id,
                ad_performance_query,
            )

            ad_performance = []

            for row in ad_rows:
                ad_cost = (
                    row.metrics.cost_micros
                    / 1_000_000
                )

                ad_conversions = safe_float(
                    row.metrics.conversions
                )

                ad_conversion_value = safe_float(
                    row.metrics.conversions_value
                )

                ad_ctr = (
                    safe_float(
                        row.metrics.ctr
                    )
                    * 100
                )

                ad_average_cpc = (
                    row.metrics.average_cpc
                    / 1_000_000
                )

                ad_conversion_rate = (
                    safe_float(
                        row.metrics
                        .conversions_from_interactions_rate
                    )
                    * 100
                )

                ad_cpa = (
                    ad_cost / ad_conversions
                    if ad_conversions > 0
                    else None
                )

                ad_roas = (
                    ad_conversion_value / ad_cost
                    if ad_cost > 0
                    else None
                )

                ad_performance.append(
                    {
                        "ad_group_id": str(
                            row.ad_group.id
                        ),
                        "ad_group_name": (
                            row.ad_group.name
                        ),
                        "ad_id": str(
                            row.ad_group_ad.ad.id
                        ),
                        "status": enum_name(
                            row.ad_group_ad.status
                        ),
                        "ad_type": enum_name(
                            row.ad_group_ad
                            .ad
                            .type
                        ),
                        "ad_strength": enum_name(
                            row.ad_group_ad
                            .ad_strength
                        ),
                        "impressions": (
                            row.metrics.impressions
                        ),
                        "clicks": (
                            row.metrics.clicks
                        ),
                        "ctr_percent": round(
                            ad_ctr,
                            2,
                        ),
                        "average_cpc": round(
                            ad_average_cpc,
                            2,
                        ),
                        "cost": round(
                            ad_cost,
                            2,
                        ),
                        "conversions": round(
                            ad_conversions,
                            2,
                        ),
                        "conversion_rate_percent": (
                            round(
                                ad_conversion_rate,
                                2,
                            )
                        ),
                        "conversion_value": round(
                            ad_conversion_value,
                            2,
                        ),
                        "cpa": (
                            round(ad_cpa, 2)
                            if ad_cpa is not None
                            else None
                        ),
                        "roas": (
                            round(ad_roas, 2)
                            if ad_roas is not None
                            else None
                        ),
                    }
                )

            eligible_ads = [
                item
                for item in ad_performance
                if item["clicks"] >= 5
            ]

            converting_ads = [
                item
                for item in eligible_ads
                if item["conversions"] > 0
            ]

            ads_without_conversions = [
                item
                for item in eligible_ads
                if (
                    item["cost"] >= 10
                    and item["conversions"] == 0
                )
            ]

            low_ctr_ads = [
                item
                for item in ad_performance
                if (
                    item["impressions"] >= 100
                    and item["ctr_percent"] < 2
                )
            ]

            best_ad_by_cpa = None
            worst_ad_by_cpa = None
            best_ad_by_roas = None
            best_ad_by_conversions = None

            if converting_ads:
                best_ad_by_cpa = min(
                    converting_ads,
                    key=lambda item: (
                        item["cpa"]
                    ),
                )

                worst_ad_by_cpa = max(
                    converting_ads,
                    key=lambda item: (
                        item["cpa"]
                    ),
                )

                best_ad_by_conversions = max(
                    converting_ads,
                    key=lambda item: (
                        item["conversions"]
                    ),
                )

                ads_with_roas = [
                    item
                    for item in converting_ads
                    if item["roas"] is not None
                ]

                if ads_with_roas:
                    best_ad_by_roas = max(
                        ads_with_roas,
                        key=lambda item: (
                            item["roas"]
                        ),
                    )

            campaign_summary[
                "ad_performance_analysis"
            ] = {
                "ads_analyzed": len(
                    ad_performance
                ),
                "ads_with_sufficient_data": len(
                    eligible_ads
                ),
                "best_by_cpa": (
                    best_ad_by_cpa
                ),
                "worst_by_cpa": (
                    worst_ad_by_cpa
                ),
                "best_by_roas": (
                    best_ad_by_roas
                ),
                "best_by_conversion_volume": (
                    best_ad_by_conversions
                ),
                "ads_spending_without_conversions": (
                    ads_without_conversions[:25]
                ),
                "low_ctr_ads": (
                    low_ctr_ads[:25]
                ),
                "performance": (
                    ad_performance[:100]
                ),
            }

            if ads_without_conversions:
                add_opportunity(
                    opportunities,
                    "HIGH",
                    "AD_PERFORMANCE",
                    (
                        "Annonces avec dépense "
                        "sans conversion"
                    ),
                    (
                        f"{len(ads_without_conversions)} "
                        f"annonce(s) ont au moins "
                        f"5 clics et 10 $ de coût "
                        f"sans conversion."
                    ),
                    (
                        "Comparer les messages, les "
                        "titres, les descriptions et "
                        "les pages de destination. "
                        "Ne pas suspendre automatiquement "
                        "une annonce."
                    ),
                    {
                        "ads": (
                            ads_without_conversions[:25]
                        ),
                    },
                )

            if low_ctr_ads:
                add_opportunity(
                    opportunities,
                    "MEDIUM",
                    "AD_LOW_CTR",
                    (
                        "Annonces avec un CTR faible"
                    ),
                    (
                        f"{len(low_ctr_ads)} annonce(s) "
                        f"ont au moins 100 impressions "
                        f"et un CTR inférieur à 2 %."
                    ),
                    (
                        "Réviser la pertinence du "
                        "message, les titres, les "
                        "descriptions et l'alignement "
                        "avec les mots-clés du groupe."
                    ),
                    {
                        "ads": low_ctr_ads[:25],
                    },
                )

            if (
                best_ad_by_cpa is not None
                and worst_ad_by_cpa is not None
                and best_ad_by_cpa["ad_id"]
                != worst_ad_by_cpa["ad_id"]
                and worst_ad_by_cpa["cpa"]
                >= best_ad_by_cpa["cpa"] * 1.5
            ):
                add_opportunity(
                    opportunities,
                    "MEDIUM",
                    "AD_CPA_GAP",
                    (
                        "Écart important de CPA "
                        "entre les annonces"
                    ),
                    (
                        f"L'annonce "
                        f"{best_ad_by_cpa['ad_id']} "
                        f"obtient un CPA de "
                        f"{best_ad_by_cpa['cpa']}, "
                        f"tandis que l'annonce "
                        f"{worst_ad_by_cpa['ad_id']} "
                        f"obtient un CPA de "
                        f"{worst_ad_by_cpa['cpa']}."
                    ),
                    (
                        "Comparer les variantes avant "
                        "toute décision. Vérifier le "
                        "volume, la durée de diffusion "
                        "et la fiabilité de l'écart."
                    ),
                    {
                        "best_ad": best_ad_by_cpa,
                        "weakest_ad": (
                            worst_ad_by_cpa
                        ),
                    },
                )

            audit_coverage[
                "ad_performance"
            ] = "SUCCESS"

        except Exception as error:
            audit_coverage[
                "ad_performance"
            ] = "FAILED"

            audit_errors.append(
                {
                    "audit": "ad_performance",
                    "error": str(error),
                }
            )

        # ----------------------------------------------------
        # 6. ANNONCES RSA - ÉTAT ACTUEL, SANS DATE
        # ----------------------------------------------------
        try:
            rsa_query = f"""
                SELECT
                    campaign.id,
                    ad_group.id,
                    ad_group.name,
                    ad_group_ad.ad.id,
                    ad_group_ad.status,
                    ad_group_ad.ad.type,
                    ad_group_ad.ad_strength,
                    ad_group_ad.ad.responsive_search_ad.headlines,
                    ad_group_ad.ad.responsive_search_ad.descriptions
                FROM ad_group_ad
                WHERE campaign.id = {campaign_id}
                  AND ad_group_ad.status != 'REMOVED'
                  AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
            """
            rsa_rows = execute_query(client, customer_id, rsa_query)
            incomplete_rsa = []

            for row in rsa_rows:
                headlines = list(row.ad_group_ad.ad.responsive_search_ad.headlines)
                descriptions = list(row.ad_group_ad.ad.responsive_search_ad.descriptions)
                headline_texts = [x.text.strip().lower() for x in headlines if x.text]
                description_texts = [x.text.strip().lower() for x in descriptions if x.text]
                duplicate_headlines = len(headline_texts) - len(set(headline_texts))
                duplicate_descriptions = len(description_texts) - len(set(description_texts))

                if (
                    len(headlines) < 15
                    or len(descriptions) < 4
                    or duplicate_headlines > 0
                    or duplicate_descriptions > 0
                ):
                    incomplete_rsa.append({
                        "ad_group": row.ad_group.name,
                        "ad_id": str(row.ad_group_ad.ad.id),
                        "status": enum_name(row.ad_group_ad.status),
                        "ad_strength": enum_name(row.ad_group_ad.ad_strength),
                        "headlines_count": len(headlines),
                        "descriptions_count": len(descriptions),
                        "missing_headlines": max(0, 15 - len(headlines)),
                        "missing_descriptions": max(0, 4 - len(descriptions)),
                        "duplicate_headlines": duplicate_headlines,
                        "duplicate_descriptions": duplicate_descriptions,
                    })

            if not rsa_rows:
                add_opportunity(
                    opportunities,
                    "INFO",
                    "RSA",
                    "Aucune RSA trouvée",
                    "Aucune RSA admissible n'a été retournée pour cette campagne.",
                    "Vérifier le type de campagne et la présence d'annonces Search actives.",
                )
            elif incomplete_rsa:
                add_opportunity(
                    opportunities,
                    "MEDIUM",
                    "RSA_COMPLETENESS",
                    "Annonces RSA incomplètes",
                    (
                        f"{len(incomplete_rsa)} RSA nécessitent une révision des titres, "
                        "descriptions ou contenus dupliqués."
                    ),
                    (
                        "Évaluer 15 titres et 4 descriptions. Tester différents CTA et "
                        "arguments. Ne publier aucun texte automatiquement."
                    ),
                    {"ads": incomplete_rsa[:25]},
                )

            audit_coverage["rsa"] = "SUCCESS"
        except Exception as error:
            audit_coverage["rsa"] = "FAILED"
            audit_errors.append({"audit": "rsa", "error": str(error)})

        # ----------------------------------------------------
        # 7. ASSETS DE CAMPAGNE - ÉTAT ACTUEL, SANS DATE
        # ----------------------------------------------------
        try:
            asset_query = f"""
                SELECT
                    campaign.id,
                    campaign_asset.field_type,
                    campaign_asset.status
                FROM campaign_asset
                WHERE campaign.id = {campaign_id}
                  AND campaign_asset.status != 'REMOVED'
            """
            asset_rows = execute_query(client, customer_id, asset_query)
            active_asset_types = sorted({
                enum_name(row.campaign_asset.field_type)
                for row in asset_rows
                if enum_name(row.campaign_asset.status) == "ENABLED"
            })
            expected_assets = {"SITELINK", "CALLOUT", "STRUCTURED_SNIPPET", "IMAGE"}
            missing_assets = sorted(expected_assets - set(active_asset_types))

            if missing_assets:
                add_opportunity(
                    opportunities,
                    "MEDIUM",
                    "MISSING_ASSETS",
                    "Composants publicitaires potentiellement manquants",
                    (
                        "Les types suivants ne sont pas actifs au niveau campagne : "
                        + ", ".join(missing_assets)
                    ),
                    (
                        "Vérifier s'ils sont applicables et s'ils existent au niveau du "
                        "compte ou du groupe avant d'en créer."
                    ),
                    {
                        "active_campaign_asset_types": active_asset_types,
                        "missing_campaign_asset_types": missing_assets,
                        "scope_checked": "CAMPAIGN",
                    },
                )

            audit_coverage["campaign_assets"] = "SUCCESS"
        except Exception as error:
            audit_coverage["campaign_assets"] = "FAILED"
            audit_errors.append({"audit": "campaign_assets", "error": str(error)})

        # ----------------------------------------------------
        # 8. TERMES DE RECHERCHE SANS CONVERSION
        # ----------------------------------------------------
        try:
            search_term_query = f"""
                SELECT
                    campaign.id,
                    ad_group.name,
                    search_term_view.search_term,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions
                FROM search_term_view
                WHERE campaign.id = {campaign_id}
                  AND {date_filter}
            """
            search_rows = execute_query(client, customer_id, search_term_query)
            wasted_terms = []

            for row in search_rows:
                item_cost = row.metrics.cost_micros / 1_000_000
                item_conversions = safe_float(row.metrics.conversions)
                if row.metrics.clicks >= 5 and item_cost >= 10 and item_conversions == 0:
                    wasted_terms.append({
                        "ad_group": row.ad_group.name,
                        "search_term": row.search_term_view.search_term,
                        "impressions": row.metrics.impressions,
                        "clicks": row.metrics.clicks,
                        "cost": round(item_cost, 2),
                        "conversions": 0,
                    })

            wasted_terms.sort(key=lambda x: x["cost"], reverse=True)
            if wasted_terms:
                total_wasted_cost = round(sum(x["cost"] for x in wasted_terms), 2)
                add_opportunity(
                    opportunities,
                    "HIGH",
                    "SEARCH_TERMS",
                    "Termes de recherche avec dépense sans conversion",
                    (
                        f"{len(wasted_terms)} terme(s) dépassent 5 clics et 10 $ "
                        "sans conversion."
                    ),
                    (
                        "Vérifier l'intention. Évaluer un négatif seulement après "
                        "validation humaine."
                    ),
                    {
                        "estimated_wasted_cost": total_wasted_cost,
                        "search_terms": wasted_terms[:50],
                    },
                )

            audit_coverage["search_terms"] = "SUCCESS"
        except Exception as error:
            audit_coverage["search_terms"] = "FAILED"
            audit_errors.append({"audit": "search_terms", "error": str(error)})

        # ----------------------------------------------------
        # 9. PERFORMANCE PAR JOUR ET HEURE
        # ----------------------------------------------------
        try:
            schedule_query = f"""
                SELECT
                    campaign.id,
                    segments.day_of_week,
                    segments.hour,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value
                FROM campaign
                WHERE campaign.id = {campaign_id}
                  AND {date_filter}
            """
            schedule_rows = execute_query(client, customer_id, schedule_query)
            weak_periods = []

            for row in schedule_rows:
                item_cost = row.metrics.cost_micros / 1_000_000
                item_conversions = safe_float(row.metrics.conversions)
                if row.metrics.clicks >= 10 and item_cost >= 25 and item_conversions == 0:
                    weak_periods.append({
                        "day": enum_name(row.segments.day_of_week),
                        "hour": row.segments.hour,
                        "impressions": row.metrics.impressions,
                        "clicks": row.metrics.clicks,
                        "cost": round(item_cost, 2),
                        "conversions": 0,
                    })

            weak_periods.sort(key=lambda x: x["cost"], reverse=True)
            if weak_periods:
                add_opportunity(
                    opportunities,
                    "MEDIUM",
                    "SCHEDULE_PERFORMANCE",
                    "Périodes avec dépense sans conversion",
                    f"{len(weak_periods)} combinaison(s) jour/heure dépassent les seuils.",
                    (
                        "Vérifier la répétition sur une période plus longue avant "
                        "d'ajuster le calendrier de diffusion."
                    ),
                    {"periods": weak_periods[:30]},
                )

            audit_coverage["schedule"] = "SUCCESS"
        except Exception as error:
            audit_coverage["schedule"] = "FAILED"
            audit_errors.append({"audit": "schedule", "error": str(error)})

        # ----------------------------------------------------
        # 10. PERFORMANCE GÉOGRAPHIQUE
        # ----------------------------------------------------
        try:
            geo_query = f"""
                SELECT
                    campaign.id,
                    geographic_view.country_criterion_id,
                    geographic_view.location_type,
                    segments.geo_target_region,
                    segments.geo_target_city,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value
                FROM geographic_view
                WHERE campaign.id = {campaign_id}
                  AND {date_filter}
            """
            geo_rows = execute_query(client, customer_id, geo_query)
            weak_locations = []

            for row in geo_rows:
                item_cost = row.metrics.cost_micros / 1_000_000
                item_conversions = safe_float(row.metrics.conversions)
                if row.metrics.clicks >= 10 and item_cost >= 50 and item_conversions == 0:
                    weak_locations.append({
                        "country_criterion_id": str(
                            row.geographic_view.country_criterion_id
                        ),
                        "location_type": enum_name(
                            row.geographic_view.location_type
                        ),
                        "region_resource": row.segments.geo_target_region,
                        "city_resource": row.segments.geo_target_city,
                        "impressions": row.metrics.impressions,
                        "clicks": row.metrics.clicks,
                        "cost": round(item_cost, 2),
                        "conversions": 0,
                    })

            weak_locations.sort(key=lambda x: x["cost"], reverse=True)
            if weak_locations:
                add_opportunity(
                    opportunities,
                    "HIGH",
                    "GEO_PERFORMANCE",
                    "Zones géographiques avec dépense sans conversion",
                    f"{len(weak_locations)} zone(s) dépassent les seuils sans conversion.",
                    (
                        "Identifier les zones, vérifier leur importance commerciale et "
                        "envisager une exclusion seulement après validation."
                    ),
                    {"locations": weak_locations[:30]},
                )

            audit_coverage["geography"] = "SUCCESS"
        except Exception as error:
            audit_coverage["geography"] = "FAILED"
            audit_errors.append({"audit": "geography", "error": str(error)})

        # ----------------------------------------------------
        # 11. AUDIENCES EN OBSERVATION - ÉTAT ACTUEL, SANS DATE
        # ----------------------------------------------------
        try:
            audience_query = f"""
                SELECT
                    campaign.id,
                    campaign_criterion.criterion_id,
                    campaign_criterion.type,
                    campaign_criterion.status,
                    campaign_criterion.negative
                FROM campaign_criterion
                WHERE campaign.id = {campaign_id}
                  AND campaign_criterion.status != 'REMOVED'
            """
            audience_rows = execute_query(client, customer_id, audience_query)
            audience_types = {
                "USER_LIST", "USER_INTEREST", "CUSTOM_AUDIENCE",
                "COMBINED_AUDIENCE", "LIFE_EVENT"
            }
            detected_audiences = []

            for row in audience_rows:
                criterion_type = enum_name(row.campaign_criterion.type)
                if criterion_type in audience_types and not row.campaign_criterion.negative:
                    detected_audiences.append({
                        "criterion_id": str(row.campaign_criterion.criterion_id),
                        "type": criterion_type,
                        "status": enum_name(row.campaign_criterion.status),
                    })

            if not detected_audiences:
                add_opportunity(
                    opportunities,
                    "LOW",
                    "AUDIENCE_OBSERVATION",
                    "Aucun segment d'audience détecté au niveau campagne",
                    "L'audit n'a trouvé aucun segment d'audience positif au niveau campagne.",
                    (
                        "Évaluer des segments en Observation sans restreindre la diffusion. "
                        "Vérifier aussi les critères des groupes d'annonces."
                    ),
                    {"campaign_audiences_found": 0, "scope_checked": "CAMPAIGN"},
                )

            audit_coverage["audiences"] = "SUCCESS"
        except Exception as error:
            audit_coverage["audiences"] = "FAILED"
            audit_errors.append({"audit": "audiences", "error": str(error)})

        # ----------------------------------------------------
        # CLASSEMENT ET SYNTHÈSE
        # ----------------------------------------------------
        opportunities.sort(key=lambda x: priority_order(x["priority"]))
        priority_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for opportunity in opportunities:
            priority = opportunity["priority"]
            if priority in priority_counts:
                priority_counts[priority] += 1

        roas_value = campaign_summary.get("roas")
        cpa_value = campaign_summary.get("cpa")
        campaign_health = "HEALTHY"
        if roas_value is not None and roas_value >= 10:
            campaign_health = "EXCELLENT"
        elif roas_value is not None and roas_value < 2:
            campaign_health = "AT_RISK"

        if roas_value is not None and cpa_value is not None:
            main_strength = f"ROAS de {roas_value} et CPA de {cpa_value}"
        elif roas_value is not None:
            main_strength = f"ROAS de {roas_value}"
        elif cpa_value is not None:
            main_strength = f"CPA de {cpa_value}"
        else:
            main_strength = "Données insuffisantes pour déterminer le principal point fort"

        main_risk = "Aucun risque majeur détecté"
        recommended_first_action = "Continuer la surveillance"
        estimated_priority = "LOW"
        high_items = [x for x in opportunities if x.get("priority") == "HIGH"]
        medium_items = [x for x in opportunities if x.get("priority") == "MEDIUM"]

        if high_items:
            first = high_items[0]
            estimated_priority = "HIGH"
            main_risk = first.get("title", "Une opportunité prioritaire a été détectée")
            recommended_first_action = first.get(
                "recommendation", "Examiner l'opportunité avant toute intervention"
            )
        elif medium_items:
            first = medium_items[0]
            estimated_priority = "MEDIUM"
            main_risk = first.get(
                "title", "Une opportunité de priorité moyenne a été détectée"
            )
            recommended_first_action = first.get(
                "recommendation", "Examiner l'opportunité avant toute intervention"
            )
            
        # ----------------------------------------------------
        # RÉPONSE JSON
        # ----------------------------------------------------

        return {
            "mode": "ON_DEMAND_ANALYSIS",
            "automatic_action": False,
            "requires_human_confirmation": True,
            "status": "RECOMMENDATION_ONLY",
            "customer_id": customer_id,
            "campaign_id": campaign_id,
            "date_range": date_range,
            "campaign": campaign_summary,
            "executive_summary": {
                "campaign_health": campaign_health,
                "main_strength": main_strength,
                "main_risk": main_risk,
                "recommended_first_action": recommended_first_action,
                "estimated_priority": estimated_priority,
            },
            "summary": {
                "opportunities_count": len(opportunities),
                "priority_counts": priority_counts,
                "audits_successful": sum(
                    1 for value in audit_coverage.values() if value == "SUCCESS"
                ),
                "audits_failed": len(audit_errors),
            },
            "opportunities": opportunities,
            "audit_coverage": audit_coverage,
            "audit_errors": audit_errors,
            "disclaimer": (
                "Cette analyse ne modifie aucune campagne. Chaque recommandation doit "
                "être validée par une personne qualifiée avant toute application."
            ),
        }

    except ValueError as error:
        return {
            "status": "FAILED",
            "campaign_id": campaign_id,
            "automatic_action": False,
            "error": str(error),
        }
    except Exception as error:
        return {
            "status": "FAILED",
            "campaign_id": campaign_id,
            "automatic_action": False,
            "error": str(error),
        }





            
 
