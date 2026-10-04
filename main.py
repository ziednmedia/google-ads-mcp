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
# ----------------------------------------------------
# AD GROUPE
# ----------------------------------------------------
@app.get("/ad-groups")
def ad_groups(
    customer_id: str,
    campaign_id: str
):
    try:

        customer_id = normalize_customer_id(
            customer_id
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

        results = []

        campaign_name = ""

        for row in response:

            campaign_name = (
                row.campaign.name
            )

            results.append(
                {
                    "ad_group_id": str(
                        row.ad_group.id
                    ),
                    "ad_group_name":
                        row.ad_group.name,
                    "status":
                        enum_name(
                            row.ad_group.status
                        ),
                    "type":
                        enum_name(
                            row.ad_group.type
                        )
                }
            )

        return {
            "customer_id":
                customer_id,
            "campaign_id":
                campaign_id,
            "campaign_name":
                campaign_name,
            "total_ad_groups":
                len(results),
            "ad_groups":
                results
        }

    except Exception as error:

        return {
            "status": "FAILED",
            "error": str(error)
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
    customer_id: str,
    campaign_id: str
):
    try:

        customer_id = normalize_customer_id(
            customer_id
        )

        client = get_google_ads_client()

        google_ads_service = client.get_service(
            "GoogleAdsService"
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
              AND segments.date DURING LAST_30_DAYS
        """

        campaign_response = (
            google_ads_service.search(
                customer_id=customer_id,
                query=campaign_query
            )
        )

        campaign_row = next(
            iter(campaign_response),
            None
        )

        if not campaign_row:
            return {
                "status": "FAILED",
                "error":
                    "Campaign not found"
            }

        cost = (
            campaign_row.metrics.cost_micros
            / 1000000
        )

        conversions = float(
            campaign_row.metrics.conversions
        )

        conversion_value = float(
            campaign_row.metrics.conversions_value
        )

        ctr = (
            float(
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
                query=ad_group_query
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
                f"{round(conversions,2)} conversions sur les 30 derniers jours"
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

        if enabled_ad_groups == total_ad_groups:

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
                round(health_score)
            )
        )

        if health_score >= 90:

            health_status = "GOOD"

        elif health_score >= 70:

            health_status = "WARNING"

        else:

            health_status = "CRITICAL"

        return {

            "campaign_id":
                str(
                    campaign_row.campaign.id
                ),

            "campaign_name":
                campaign_row.campaign.name,

            "campaign_status":
                enum_name(
                    campaign_row.campaign.status
                ),

            "campaign_type":
                enum_name(
                    campaign_row
                    .campaign
                    .advertising_channel_type
                ),

            "budget":
                round(
                    campaign_row
                    .campaign_budget
                    .amount_micros
                    / 1000000,
                    2
                ),

            "last_30_days": {

                "impressions":
                    campaign_row.metrics.impressions,

                "clicks":
                    campaign_row.metrics.clicks,

                "ctr_percent":
                    round(
                        ctr,
                        2
                    ),

                "cost":
                    round(
                        cost,
                        2
                    ),

                "conversions":
                    round(
                        conversions,
                        2
                    ),

                "conversion_value":
                    round(
                        conversion_value,
                        2
                    ),

                "cpa":
                    round(
                        cpa,
                        2
                    )
                    if cpa
                    else None,

                "roas":
                    round(
                        roas,
                        2
                    )
                    if roas
                    else None
            },

            "ad_groups": {

                "total":
                    total_ad_groups,

                "enabled":
                    enabled_ad_groups,

                "paused":
                    paused_ad_groups
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
                        recommendations
         } 
            
        }

    except Exception as error:

        return {
            "status": "FAILED",
            "error": str(error)
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
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM campaign
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
            conversion_value = safe_float(
                row.metrics.conversions_value
            )

            cpa = (
                round(cost / conversions, 2)
                if conversions > 0
                else None
            )

            roas = (
                round(conversion_value / cost, 2)
                if cost > 0
                else None
            )

            data.append(
                {
                    "campaign_id": str(row.campaign.id),
                    "campaign_name": row.campaign.name,
                    "status": enum_name(row.campaign.status),
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "ctr": round(
                        safe_float(row.metrics.ctr) * 100,
                        2,
                    ),
                    "cost": round(cost, 2),
                    "conversions": round(conversions, 2),
                    "conversion_value": round(
                        conversion_value,
                        2,
                    ),
                    "cpa": cpa,
                    "roas": roas,
                }
            )

        return data

    except Exception as error:
        return {"error": str(error)}


# ============================================================
# TOP CAMPAGNES
# ============================================================

@app.get("/top-campaigns")
def top_campaigns(
    limit: int = Query(default=10, ge=1, le=50),
):
    performance = campaign_performance()

    if isinstance(performance, dict) and "error" in performance:
        return performance

    campaigns_with_roas = [
        campaign
        for campaign in performance
        if campaign.get("roas") is not None
    ]

    campaigns_with_roas.sort(
        key=lambda value: value["roas"],
        reverse=True,
    )

    return campaigns_with_roas[:limit]


# ============================================================
# MOTS-CLÉS
# ============================================================

@app.get("/keywords")
def keywords(
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
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.cost_micros,
                metrics.conversions
            FROM keyword_view
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
                    "criterion_id": str(
                        row.ad_group_criterion.criterion_id
                    ),
                    "keyword": (
                        row.ad_group_criterion.keyword.text
                    ),
                    "match_type": enum_name(
                        row.ad_group_criterion
                        .keyword.match_type
                    ),
                    "status": enum_name(
                        row.ad_group_criterion.status
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
# SEARCH TERMES
# ============================================================
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
            "Période Google Ads prédéfinie. "
            "La valeur par défaut est "
            "LAST_30_DAYS."
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
                metrics.conversions_value
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

        return {
            "status": "SUCCESS",
            "customer_id": customer_id,
            "campaign_id": campaign_id,
            "campaign_name": (
                campaign_name
            ),
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
            "search_terms_count": len(
                results
            ),
            "search_terms": results,
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

    customer_id: str,

    campaign_id: str = Query(
        ...,
        description="ID Google Ads de la campagne à analyser",
    ),
):
    campaign_id = campaign_id.replace("-", "").strip()
    

    try:
        client = get_google_ads_client()

        customer_id = normalize_customer_id(
                customer_id
        )

        opportunities: List[Dict[str, Any]] = []
        audit_errors: List[Dict[str, str]] = []
        audit_coverage: Dict[str, str] = {}

        campaign_summary: Dict[str, Any] = {
            "campaign_id": campaign_id,
            "period": "LAST_30_DAYS",
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
                  AND segments.date DURING LAST_30_DAYS
            """

            rows = execute_query(
    client,
    customer_id,
    performance_query
)

            if not rows:

                   return {

                        "campaign_id": campaign_id,

                        "status": "NO_RECENT_DATA",

                        "message":
                            "Aucune donnée durant LAST_30_DAYS.",

                        "customer_id": customer_id,

                        "automatic_action": False
                    }

            row = rows[0]

            cost = row.metrics.cost_micros / 1_000_000
            conversions = safe_float(row.metrics.conversions)
            conversion_value = safe_float(
                row.metrics.conversions_value
            )

            cpa = (
                round(cost / conversions, 2)
                if conversions > 0
                else None
            )

            roas = (
                round(conversion_value / cost, 2)
                if cost > 0
                else None
            )

            ctr = round(
                safe_float(row.metrics.ctr) * 100,
                2,
            )

            impression_share = safe_float(
                row.metrics.search_impression_share
            )

            lost_budget = safe_float(
                row.metrics
                .search_budget_lost_impression_share
            )

            lost_rank = safe_float(
                row.metrics
                .search_rank_lost_impression_share
            )

            daily_budget = (
                row.campaign_budget.amount_micros
                / 1_000_000
            )

            campaign_summary.update(
                {
                    "campaign_name": row.campaign.name,
                    "status": enum_name(
                        row.campaign.status
                    ),
                    "channel_type": enum_name(
                        row.campaign
                        .advertising_channel_type
                    ),
                    "bidding_strategy": enum_name(
                        row.campaign
                        .bidding_strategy_type
                    ),
                    "daily_budget": round(
                        daily_budget,
                        2,
                    ),
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "ctr_percent": ctr,
                    "cost": round(cost, 2),
                    "conversions": round(
                        conversions,
                        2,
                    ),
                    "conversion_value": round(
                        conversion_value,
                        2,
                    ),
                    "cpa": cpa,
                    "roas": roas,
                    "search_impression_share_percent": (
                        round(impression_share * 100, 2)
                        if impression_share > 0
                        else None
                    ),
                    "lost_budget_share_percent": (
                        round(lost_budget * 100, 2)
                        if lost_budget > 0
                        else 0
                    ),
                    "lost_rank_share_percent": (
                        round(lost_rank * 100, 2)
                        if lost_rank > 0
                        else 0
                    ),
                }
            )

            audit_coverage["campaign_performance"] = "SUCCESS"

            non_smart_strategies = {
                "MANUAL_CPC",
                "MANUAL_CPM",
                "MANUAL_CPV",
                "COMMISSION",
            }

            bidding_strategy = enum_name(
                row.campaign.bidding_strategy_type
            )

            if (
                conversions >= 30
                and bidding_strategy in non_smart_strategies
            ):
                add_opportunity(
                    opportunities,
                    "MEDIUM",
                    "BIDDING_STRATEGY",
                    "Volume suffisant pour évaluer une stratégie intelligente",
                    (
                        f"La campagne a généré "
                        f"{round(conversions, 2)} conversions "
                        f"durant les 30 derniers jours et utilise "
                        f"{bidding_strategy}."
                    ),
                    (
                        "Évaluer Maximiser les conversions ou CPA "
                        "cible. Vérifier d'abord la qualité du suivi "
                        "des conversions et la stabilité du CPA."
                    ),
                    {
                        "conversions_30d": round(
                            conversions,
                            2,
                        ),
                        "current_strategy": bidding_strategy,
                        "observed_cpa": cpa,
                    },
                )

            if lost_budget >= 0.20:
                if (
                    conversions >= 10
                    and roas is not None
                    and roas >= 2
                ):
                    add_opportunity(
                        opportunities,
                        "HIGH",
                        "IMPRESSION_SHARE_BUDGET",
                        "Part d'impressions perdue à cause du budget",
                        (
                            f"La campagne perd environ "
                            f"{round(lost_budget * 100, 2)} % "
                            f"des impressions à cause du budget."
                        ),
                        (
                            "La campagne produit des conversions et "
                            "un ROAS positif. Évaluer une augmentation "
                            "progressive du budget après validation."
                        ),
                        {
                            "lost_budget_share_percent": round(
                                lost_budget * 100,
                                2,
                            ),
                            "conversions": round(
                                conversions,
                                2,
                            ),
                            "cpa": cpa,
                            "roas": roas,
                            "current_daily_budget": round(
                                daily_budget,
                                2,
                            ),
                        },
                    )
                else:
                    add_opportunity(
                        opportunities,
                        "MEDIUM",
                        "IMPRESSION_SHARE_BUDGET",
                        "Part d'impressions perdue à cause du budget",
                        (
                            f"La campagne perd environ "
                            f"{round(lost_budget * 100, 2)} % "
                            f"des impressions à cause du budget."
                        ),
                        (
                            "Ne pas augmenter automatiquement le "
                            "budget. Examiner d'abord le CPA, le ROAS "
                            "et la qualité des conversions."
                        ),
                        {
                            "lost_budget_share_percent": round(
                                lost_budget * 100,
                                2,
                            ),
                            "conversions": round(
                                conversions,
                                2,
                            ),
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
                        f"La campagne perd environ "
                        f"{round(lost_rank * 100, 2)} % "
                        f"des impressions à cause du classement."
                    ),
                    (
                        "Analyser le Quality Score, la pertinence des "
                        "annonces, le CTR attendu, l'expérience de "
                        "page de destination et les enchères."
                    ),
                    {
                        "lost_rank_share_percent": round(
                            lost_rank * 100,
                            2,
                        ),
                        "ctr_percent": ctr,
                        "cpa": cpa,
                    },
                )

        except Exception as error:
            audit_coverage["campaign_performance"] = "FAILED"
            audit_errors.append(
                {
                    "audit": "campaign_performance",
                    "error": str(error),
                }
            )


        # ----------------------------------------------------
        # ANALYSE COMPARATIVE DES GROUPES D'ANNONCES
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
                  AND segments.date DURING LAST_30_DAYS
                ORDER BY metrics.cost_micros DESC
            """

            ad_group_rows = execute_query(
                client,
                customer_id,
                ad_group_query
            )

            ad_group_performance = []

            for row in ad_group_rows:
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

                average_cpc = (
                    row.metrics.average_cpc
                    / 1_000_000
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

                ad_group_performance.append(
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
                        "conversion_rate_percent": round(
                            conversion_rate,
                            2
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
                        )
                    }
                )

            eligible_for_comparison = [
                item
                for item in ad_group_performance
                if item["clicks"] >= 5
            ]

            groups_with_conversions = [
                item
                for item in eligible_for_comparison
                if item["conversions"] > 0
            ]

            groups_without_conversions = [
                item
                for item in eligible_for_comparison
                if (
                    item["cost"] >= 10
                    and item["conversions"] == 0
                )
            ]

            best_by_cpa = None
            worst_by_cpa = None
            best_by_roas = None
            best_by_conversions = None

            if groups_with_conversions:
                best_by_cpa = min(
                    groups_with_conversions,
                    key=lambda item: item["cpa"]
                )

                worst_by_cpa = max(
                    groups_with_conversions,
                    key=lambda item: item["cpa"]
                )

                best_by_conversions = max(
                    groups_with_conversions,
                    key=lambda item: (
                        item["conversions"]
                    )
                )

                groups_with_roas = [
                    item
                    for item in groups_with_conversions
                    if item["roas"] is not None
                ]

                if groups_with_roas:
                    best_by_roas = max(
                        groups_with_roas,
                        key=lambda item: item["roas"]
                    )

            ad_group_comparison = {
                "total_ad_groups": len(
                    ad_group_performance
                ),
                "groups_with_sufficient_data": len(
                    eligible_for_comparison
                ),
                "best_by_cpa": best_by_cpa,
                "worst_by_cpa": worst_by_cpa,
                "best_by_roas": best_by_roas,
                "best_by_conversion_volume": (
                    best_by_conversions
                ),
                "groups_spending_without_conversions": (
                    groups_without_conversions
                )
            }

            campaign_summary[
                "ad_group_analysis"
            ] = {
                "performance": (
                    ad_group_performance
                ),
                "comparison": (
                    ad_group_comparison
                )
            }

            if groups_without_conversions:
                add_opportunity(
                    opportunities,
                    "HIGH",
                    "AD_GROUP_NO_CONVERSIONS",
                    (
                        "Groupes d'annonces avec "
                        "dépense sans conversion"
                    ),
                    (
                        f"{len(groups_without_conversions)} "
                        "groupe(s) d'annonces ont dépensé "
                        "au moins 10 $ avec un minimum de "
                        "5 clics sans générer de conversion."
                    ),
                    (
                        "Examiner les mots-clés, termes de "
                        "recherche, annonces et pages de "
                        "destination de ces groupes. "
                        "Ne pas les mettre en pause "
                        "automatiquement."
                    ),
                    {
                        "ad_groups": (
                            groups_without_conversions
                        )
                    }
                )

            if (
                best_by_cpa is not None
                and worst_by_cpa is not None
                and best_by_cpa["ad_group_id"]
                != worst_by_cpa["ad_group_id"]
                and worst_by_cpa["cpa"]
                >= best_by_cpa["cpa"] * 1.5
            ):
                add_opportunity(
                    opportunities,
                    "MEDIUM",
                    "AD_GROUP_CPA_GAP",
                    (
                        "Écart important de CPA entre "
                        "les groupes d'annonces"
                    ),
                    (
                        f"Le groupe "
                        f"{best_by_cpa['ad_group_name']} "
                        f"obtient un CPA de "
                        f"{best_by_cpa['cpa']}, tandis que "
                        f"{worst_by_cpa['ad_group_name']} "
                        f"obtient un CPA de "
                        f"{worst_by_cpa['cpa']}."
                    ),
                    (
                        "Comparer les intentions de recherche, "
                        "les mots-clés, les annonces et les "
                        "pages de destination. Évaluer une "
                        "réallocation prudente seulement après "
                        "validation humaine."
                    ),
                    {
                        "best_ad_group": best_by_cpa,
                        "weakest_ad_group": (
                            worst_by_cpa
                        )
                    }
                )

            audit_coverage[
                "ad_group_comparison"
            ] = "SUCCESS"

        except Exception as error:
            audit_coverage[
                "ad_group_comparison"
            ] = "FAILED"

            audit_errors.append(
                {
                    "audit": (
                        "ad_group_comparison"
                    ),
                    "error": str(error)
                }
            )

        # ----------------------------------------------------
        # 2. QUALITY SCORE ET TYPES DE CORRESPONDANCE
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
                  AND segments.date DURING LAST_30_DAYS
            """

            keyword_rows = execute_query(
    client,
    customer_id,
    keyword_query,
)

            low_quality_keywords = []
            broad_waste_keywords = []

            for row in keyword_rows:
                keyword = (
                    row.ad_group_criterion.keyword.text
                )

                match_type = enum_name(
                    row.ad_group_criterion
                    .keyword.match_type
                )

                quality_score = (
                    row.ad_group_criterion
                    .quality_info.quality_score
                )

                ad_relevance = enum_name(
                    row.ad_group_criterion
                    .quality_info.creative_quality_score
                )

                landing_page = enum_name(
                    row.ad_group_criterion
                    .quality_info.post_click_quality_score
                )

                expected_ctr = enum_name(
                    row.ad_group_criterion
                    .quality_info.search_predicted_ctr
                )

                cost = (
                    row.metrics.cost_micros
                    / 1_000_000
                )

                conversions = safe_float(
                    row.metrics.conversions
                )

                if quality_score > 0 and quality_score <= 5:
                    low_quality_keywords.append(
                        {
                            "ad_group": row.ad_group.name,
                            "keyword": keyword,
                            "quality_score": quality_score,
                            "ad_relevance": ad_relevance,
                            "expected_ctr": expected_ctr,
                            "landing_page_experience": (
                                landing_page
                            ),
                            "impressions": (
                                row.metrics.impressions
                            ),
                            "clicks": row.metrics.clicks,
                            "cost": round(cost, 2),
                            "conversions": round(
                                conversions,
                                2,
                            ),
                        }
                    )

                if (
                    match_type == "BROAD"
                    and row.metrics.clicks >= 5
                    and conversions == 0
                    and cost >= 10
                ):
                    broad_waste_keywords.append(
                        {
                            "ad_group": row.ad_group.name,
                            "keyword": keyword,
                            "match_type": match_type,
                            "clicks": row.metrics.clicks,
                            "cost": round(cost, 2),
                            "conversions": 0,
                        }
                    )

            low_quality_keywords.sort(
                key=lambda item: (
                    item["quality_score"],
                    -item["cost"],
                )
            )

            broad_waste_keywords.sort(
                key=lambda item: item["cost"],
                reverse=True,
            )

            if low_quality_keywords:
                add_opportunity(
                    opportunities,
                    "HIGH",
                    "QUALITY_SCORE",
                    "Mots-clés avec un faible Quality Score",
                    (
                        f"{len(low_quality_keywords)} mot(s)-clé(s) "
                        f"ont un Quality Score de 5 ou moins."
                    ),
                    (
                        "Vérifier séparément la pertinence de "
                        "l'annonce, le CTR attendu et l'expérience "
                        "sur la page de destination."
                    ),
                    {
                        "keywords": low_quality_keywords[:25]
                    },
                )

            if broad_waste_keywords:
                add_opportunity(
    opportunities,
    "HIGH",
    "MATCH_TYPE",
    "Requêtes larges avec dépense sans conversion",
    (
        f"{len(broad_waste_keywords)} mot(s)-clé(s) "
        f"en requête large ont au moins 5 clics, "
        f"10 $ de coût et aucune conversion."
    ),
    (
        "Examiner les termes de recherche. Évaluer "
        "Phrase Match, Exact Match ou des mots-clés "
        "négatifs. Ne pas changer automatiquement le "
        "type de correspondance."
    ),
    {
        "keywords": broad_waste_keywords[:25]
    },
)

            audit_coverage["keyword_quality"] = "SUCCESS"

        except Exception as error:
            audit_coverage["keyword_quality"] = "FAILED"
            audit_errors.append(
                {
                    "audit": "keyword_quality",
                    "error": str(error),
                }
            )

        # ----------------------------------------------------
        # 3. ANNONCES RSA : 15 TITRES ET 4 DESCRIPTIONS
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

            rsa_rows = execute_query(
    client,
    customer_id,
    rsa_query
)

            incomplete_rsa = []

            for row in rsa_rows:
                headlines = list(
                    row.ad_group_ad.ad
                    .responsive_search_ad.headlines
                )

                descriptions = list(
                    row.ad_group_ad.ad
                    .responsive_search_ad.descriptions
                )

                headline_texts = [
                    asset.text.strip().lower()
                    for asset in headlines
                    if asset.text
                ]

                description_texts = [
                    asset.text.strip().lower()
                    for asset in descriptions
                    if asset.text
                ]

                duplicate_headlines = (
                    len(headline_texts)
                    - len(set(headline_texts))
                )

                duplicate_descriptions = (
                    len(description_texts)
                    - len(set(description_texts))
                )

                if (
                    len(headlines) < 15
                    or len(descriptions) < 4
                    or duplicate_headlines > 0
                    or duplicate_descriptions > 0
                ):
                    incomplete_rsa.append(
                        {
                            "ad_group": row.ad_group.name,
                            "ad_id": str(
                                row.ad_group_ad.ad.id
                            ),
                            "status": enum_name(
                                row.ad_group_ad.status
                            ),
                            "ad_strength": enum_name(
                                row.ad_group_ad.ad_strength
                            ),
                            "headlines_count": len(
                                headlines
                            ),
                            "descriptions_count": len(
                                descriptions
                            ),
                            "missing_headlines": max(
                                0,
                                15 - len(headlines),
                            ),
                            "missing_descriptions": max(
                                0,
                                4 - len(descriptions),
                            ),
                            "duplicate_headlines": (
                                duplicate_headlines
                            ),
                            "duplicate_descriptions": (
                                duplicate_descriptions
                            ),
                        }
                    )

            if not rsa_rows:
                add_opportunity(
                    opportunities,
                    "INFO",
                    "RSA",
                    "Aucune RSA trouvée",
                    (
                        "Aucune annonce de recherche réactive "
                        "admissible n'a été retournée pour cette "
                        "campagne."
                    ),
                    (
                        "Vérifier le type de campagne et la présence "
                        "d'annonces Search actives."
                    ),
                )

            elif incomplete_rsa:
                add_opportunity(
                    opportunities,
                    "MEDIUM",
                    "RSA_COMPLETENESS",
                    "Annonces RSA incomplètes",
                    (
                        f"{len(incomplete_rsa)} RSA nécessitent "
                        f"une révision des titres, descriptions ou "
                        f"contenus dupliqués."
                    ),
                    (
                        "Évaluer l'utilisation de 15 titres et "
                        "4 descriptions. Tester différents CTA, "
                        "arguments de valeur et formulations. "
                        "Ne publier aucun texte automatiquement."
                    ),
                    {
                        "ads": incomplete_rsa[:25]
                    },
                )

            audit_coverage["rsa"] = "SUCCESS"

        except Exception as error:
            audit_coverage["rsa"] = "FAILED"
            audit_errors.append(
                {
                    "audit": "rsa",
                    "error": str(error),
                }
            )

        # ----------------------------------------------------
        # 4. ASSETS DE CAMPAGNE
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

            asset_rows = execute_query(
    client,
    customer_id,
    asset_query
)

            active_asset_types = sorted(
                {
                    enum_name(
                        row.campaign_asset.field_type
                    )
                    for row in asset_rows
                    if enum_name(
                        row.campaign_asset.status
                    ) == "ENABLED"
                }
            )

            expected_assets = {
                "SITELINK",
                "CALLOUT",
                "STRUCTURED_SNIPPET",
                "IMAGE",
            }

            missing_assets = sorted(
                expected_assets
                - set(active_asset_types)
            )

            if missing_assets:
                add_opportunity(
                    opportunities,
                    "MEDIUM",
                    "MISSING_ASSETS",
                    "Composants publicitaires potentiellement manquants",
                    (
                        "Les types de composants suivants ne sont "
                        "pas actifs au niveau campagne : "
                        + ", ".join(missing_assets)
                    ),
                    (
                        "Vérifier si ces composants sont applicables "
                        "à la campagne et s'ils existent au niveau "
                        "du compte ou du groupe d'annonces avant "
                        "d'en créer de nouveaux."
                    ),
                    {
                        "active_campaign_asset_types": (
                            active_asset_types
                        ),
                        "missing_campaign_asset_types": (
                            missing_assets
                        ),
                        "scope_checked": "CAMPAIGN",
                    },
                )

            audit_coverage["campaign_assets"] = "SUCCESS"

        except Exception as error:
            audit_coverage["campaign_assets"] = "FAILED"
            audit_errors.append(
                {
                    "audit": "campaign_assets",
                    "error": str(error),
                }
            )

        # ----------------------------------------------------
        # 5. TERMES DE RECHERCHE SANS CONVERSION
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
                  AND segments.date DURING LAST_30_DAYS
            """

            search_rows = execute_query(
    client,
    customer_id,
    search_term_query
)

            wasted_terms = []

            for row in search_rows:
                cost = (
                    row.metrics.cost_micros
                    / 1_000_000
                )

                conversions = safe_float(
                    row.metrics.conversions
                )

                if (
                    row.metrics.clicks >= 5
                    and cost >= 10
                    and conversions == 0
                ):
                    wasted_terms.append(
                        {
                            "ad_group": row.ad_group.name,
                            "search_term": (
                                row.search_term_view
                                .search_term
                            ),
                            "impressions": (
                                row.metrics.impressions
                            ),
                            "clicks": row.metrics.clicks,
                            "cost": round(cost, 2),
                            "conversions": 0,
                        }
                    )

            wasted_terms.sort(
                key=lambda item: item["cost"],
                reverse=True,
            )

            if wasted_terms:
                total_wasted_cost = round(
                    sum(
                        item["cost"]
                        for item in wasted_terms
                    ),
                    2,
                )

                add_opportunity(
                    opportunities,
                    "HIGH",
                    "SEARCH_TERMS",
                    "Termes de recherche avec dépense sans conversion",
                    (
                        f"{len(wasted_terms)} terme(s) ont dépassé "
                        f"le seuil de 5 clics et 10 $ sans conversion."
                    ),
                    (
                        "Vérifier l'intention de chaque terme. "
                        "Évaluer un mot-clé négatif seulement après "
                        "validation humaine."
                    ),
                    {
                        "estimated_wasted_cost": (
                            total_wasted_cost
                        ),
                        "search_terms": wasted_terms[:50],
                    },
                )

            audit_coverage["search_terms"] = "SUCCESS"

        except Exception as error:
            audit_coverage["search_terms"] = "FAILED"
            audit_errors.append(
                {
                    "audit": "search_terms",
                    "error": str(error),
                }
            )

        # ----------------------------------------------------
        # 6. PERFORMANCE PAR JOUR ET HEURE
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
                  AND segments.date DURING LAST_30_DAYS
            """

            schedule_rows = execute_query(
    client,
    customer_id,
    schedule_query
)

            weak_periods = []

            for row in schedule_rows:
                cost = (
                    row.metrics.cost_micros
                    / 1_000_000
                )

                conversions = safe_float(
                    row.metrics.conversions
                )

                if (
                    row.metrics.clicks >= 10
                    and cost >= 25
                    and conversions == 0
                ):
                    weak_periods.append(
                        {
                            "day": enum_name(
                                row.segments.day_of_week
                            ),
                            "hour": row.segments.hour,
                            "impressions": (
                                row.metrics.impressions
                            ),
                            "clicks": row.metrics.clicks,
                            "cost": round(cost, 2),
                            "conversions": 0,
                        }
                    )

            weak_periods.sort(
                key=lambda item: item["cost"],
                reverse=True,
            )

            if weak_periods:
                add_opportunity(
                    opportunities,
                    "MEDIUM",
                    "SCHEDULE_PERFORMANCE",
                    "Périodes avec dépense sans conversion",
                    (
                        f"{len(weak_periods)} combinaison(s) "
                        f"jour/heure dépassent les seuils définis."
                    ),
                    (
                        "Vérifier la répétition de cette tendance sur "
                        "une période plus longue avant d'ajuster le "
                        "calendrier de diffusion."
                    ),
                    {
                        "periods": weak_periods[:30]
                    },
                )

            audit_coverage["schedule"] = "SUCCESS"

        except Exception as error:
            audit_coverage["schedule"] = "FAILED"
            audit_errors.append(
                {
                    "audit": "schedule",
                    "error": str(error),
                }
            )

        # ----------------------------------------------------
        # 7. PERFORMANCE GÉOGRAPHIQUE
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
                  AND segments.date DURING LAST_30_DAYS
            """

            geo_rows = execute_query(
    client,
    customer_id,
    geo_query
)

            weak_locations = []

            for row in geo_rows:
                cost = (
                    row.metrics.cost_micros
                    / 1_000_000
                )

                conversions = safe_float(
                    row.metrics.conversions
                )

                if (
                    row.metrics.clicks >= 10
                    and cost >= 50
                    and conversions == 0
                ):
                    weak_locations.append(
                        {
                            "country_criterion_id": str(
                                row.geographic_view
                                .country_criterion_id
                            ),
                            "location_type": enum_name(
                                row.geographic_view
                                .location_type
                            ),
                            "region_resource": (
                                row.segments
                                .geo_target_region
                            ),
                            "city_resource": (
                                row.segments
                                .geo_target_city
                            ),
                            "impressions": (
                                row.metrics.impressions
                            ),
                            "clicks": row.metrics.clicks,
                            "cost": round(cost, 2),
                            "conversions": 0,
                        }
                    )

            weak_locations.sort(
                key=lambda item: item["cost"],
                reverse=True,
            )

            if weak_locations:
                add_opportunity(
                    opportunities,
                    "HIGH",
                    "GEO_PERFORMANCE",
                    "Zones géographiques avec dépense sans conversion",
                    (
                        f"{len(weak_locations)} zone(s) dépassent "
                        f"les seuils minimums sans conversion."
                    ),
                    (
                        "Identifier précisément les zones, vérifier "
                        "leur importance commerciale et envisager une "
                        "exclusion seulement après validation."
                    ),
                    {
                        "locations": weak_locations[:30]
                    },
                )

            audit_coverage["geography"] = "SUCCESS"

        except Exception as error:
            audit_coverage["geography"] = "FAILED"
            audit_errors.append(
                {
                    "audit": "geography",
                    "error": str(error),
                }
            )

        # ----------------------------------------------------
        # 8. AUDIENCES EN OBSERVATION
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

            audience_rows = execute_query(
    client,
    customer_id,
    audience_query
)

            audience_types = {
                "USER_LIST",
                "USER_INTEREST",
                "CUSTOM_AUDIENCE",
                "COMBINED_AUDIENCE",
                "LIFE_EVENT",
            }

            detected_audiences = []

            for row in audience_rows:
                criterion_type = enum_name(
                    row.campaign_criterion.type
                )

                if (
                    criterion_type in audience_types
                    and not row.campaign_criterion.negative
                ):
                    detected_audiences.append(
                        {
                            "criterion_id": str(
                                row.campaign_criterion
                                .criterion_id
                            ),
                            "type": criterion_type,
                            "status": enum_name(
                                row.campaign_criterion.status
                            ),
                        }
                    )

            if not detected_audiences:
                add_opportunity(
                    opportunities,
                    "LOW",
                    "AUDIENCE_OBSERVATION",
                    "Aucun segment d'audience détecté au niveau campagne",
                    (
                        "L'audit n'a trouvé aucun segment d'audience "
                        "positif au niveau de la campagne."
                    ),
                    (
                        "Évaluer l'ajout de segments en mode "
                        "Observation pour collecter des données sans "
                        "restreindre la diffusion. Vérifier également "
                        "les critères présents au niveau des groupes "
                        "d'annonces."
                    ),
                    {
                        "campaign_audiences_found": 0,
                        "scope_checked": "CAMPAIGN",
                    },
                )

            audit_coverage["audiences"] = "SUCCESS"

        except Exception as error:
            audit_coverage["audiences"] = "FAILED"
            audit_errors.append(
                {
                    "audit": "audiences",
                    "error": str(error),
                }
            )

        # ----------------------------------------------------
        # CLASSEMENT FINAL
        # ----------------------------------------------------

        opportunities.sort(
            key=lambda item: priority_order(
                item["priority"]
            )
        )

        priority_counts = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFO": 0,
        }

        for opportunity in opportunities:
            current_priority = opportunity["priority"]

            if current_priority in priority_counts:
                priority_counts[current_priority] += 1

        # ----------------------------------------------------
        # SYNTHÈSE EXÉCUTIVE
        # ----------------------------------------------------

        roas_value = campaign_summary.get("roas")
        cpa_value = campaign_summary.get("cpa")

        campaign_health = "HEALTHY"

        if roas_value is not None and roas_value >= 10:
            campaign_health = "EXCELLENT"
        elif roas_value is not None and roas_value < 2:
            campaign_health = "AT_RISK"

        if roas_value is not None and cpa_value is not None:
            main_strength = (
                f"ROAS de {roas_value} et CPA de {cpa_value}"
            )
        elif roas_value is not None:
            main_strength = f"ROAS de {roas_value}"
        elif cpa_value is not None:
            main_strength = f"CPA de {cpa_value}"
        else:
            main_strength = (
                "Données insuffisantes pour déterminer "
                "le principal point fort"
            )

        main_risk = "Aucun risque majeur détecté"
        recommended_first_action = "Continuer la surveillance"
        estimated_priority = "LOW"

        high_priority_opportunities = [
            opportunity
            for opportunity in opportunities
            if opportunity.get("priority") == "HIGH"
        ]

        medium_priority_opportunities = [
            opportunity
            for opportunity in opportunities
            if opportunity.get("priority") == "MEDIUM"
        ]

        if high_priority_opportunities:
            estimated_priority = "HIGH"

            first_priority_opportunity = (
                high_priority_opportunities[0]
            )

            main_risk = first_priority_opportunity.get(
                "title",
                "Une opportunité prioritaire a été détectée",
            )

            recommended_first_action = (
                first_priority_opportunity.get(
                    "recommendation",
                    (
                        "Examiner l’opportunité avant "
                        "toute intervention"
                    ),
                )
            )

        elif medium_priority_opportunities:
            estimated_priority = "MEDIUM"

            first_priority_opportunity = (
                medium_priority_opportunities[0]
            )

            main_risk = first_priority_opportunity.get(
                "title",
                (
                    "Une opportunité de priorité moyenne "
                    "a été détectée"
                ),
            )

            recommended_first_action = (
                first_priority_opportunity.get(
                    "recommendation",
                    (
                        "Examiner l’opportunité avant "
                        "toute intervention"
                    ),
                )
            )




        # ----------------------------------------------------
        # RÉPONSE JSON
        # ----------------------------------------------------

        return {
            "mode": "ON_DEMAND_ANALYSIS",
            "automatic_action": False,
            "requires_human_confirmation": True,
            "status": "RECOMMENDATION_ONLY",
            "campaign": campaign_summary,
            "executive_summary": {
                "campaign_health": campaign_health,
                "main_strength": main_strength,
                "main_risk": main_risk,
                "recommended_first_action": (
                    recommended_first_action
                ),
                "estimated_priority": estimated_priority,
            },
            "summary": {
                "opportunities_count": len(
                    opportunities
                ),
                "priority_counts": priority_counts,
                "audits_successful": sum(
                    1
                    for value in audit_coverage.values()
                    if value == "SUCCESS"
                ),
                "audits_failed": len(audit_errors),
            },
            "opportunities": opportunities,
            "audit_coverage": audit_coverage,
            "audit_errors": audit_errors,
            "disclaimer": (
                "Cette analyse ne modifie aucune campagne. "
                "Chaque recommandation doit être validée par "
                "une personne qualifiée avant toute application."
            ),
        }

    except Exception as error:
        return {
            "error": str(error),
            "campaign_id": campaign_id,
            "automatic_action": False,
        }

    except Exception as error:
        return {
            "error": str(error),
            "campaign_id": campaign_id,
            "automatic_action": False,
        }

            
 
