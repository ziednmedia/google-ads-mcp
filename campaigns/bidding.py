from typing import Dict, Any

from google.ads.googleads.client import GoogleAdsClient


# ============================================================
# BIDDING STRATEGY DETAILS - Celle-là sert à analyser une seule campagne
# ============================================================
def get_bidding_strategy_details(
    client: GoogleAdsClient,
    customer_id: str,
    campaign_id: str,
) -> Dict[str, Any]:
    """
    Retourne les informations d'enchères d'une campagne.
    """

    gaql = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.bidding_strategy_type,
            campaign.bidding_strategy,
            campaign.target_cpa.target_cpa_micros,
            campaign.target_roas.target_roas,
            campaign.manual_cpc.enhanced_cpc_enabled
        FROM campaign
        WHERE campaign.id = {campaign_id}
        LIMIT 1
    """

    google_ads_service = client.get_service(
        "GoogleAdsService"
    )

    response = google_ads_service.search(
        customer_id=customer_id,
        query=gaql,
    )

    rows = list(response)

    if not rows:
        raise ValueError(
            f"Campaign {campaign_id} not found."
        )

    row = rows[0]

    target_cpa = None

    try:
        if (
            row.campaign.target_cpa
            and row.campaign.target_cpa.target_cpa_micros
        ):
            target_cpa = round(
                row.campaign.target_cpa.target_cpa_micros
                / 1_000_000,
                2,
            )
    except Exception:
        target_cpa = None

    target_roas = None

    try:
        if (
            row.campaign.target_roas
            and row.campaign.target_roas.target_roas
        ):
            target_roas = round(
                float(
                    row.campaign.target_roas.target_roas
                ),
                2,
            )
    except Exception:
        target_roas = None

    enhanced_cpc = False

    try:
        enhanced_cpc = bool(
            row.campaign.manual_cpc
            .enhanced_cpc_enabled
        )
    except Exception:
        pass

    portfolio_strategy = None

    try:
        if row.campaign.bidding_strategy:
            portfolio_strategy = (
                row.campaign.bidding_strategy
            )
    except Exception:
        pass

    return {
        "campaign_id": str(
            row.campaign.id
        ),
        "campaign_name": (
            row.campaign.name
        ),
        "status": str(
            row.campaign.status.name
        ),
        "strategy_type": str(
            row.campaign
            .bidding_strategy_type
            .name
        ),
        "target_cpa": target_cpa,
        "target_roas": target_roas,
        "portfolio_strategy": (
            portfolio_strategy
        ),
        "enhanced_cpc": enhanced_cpc,
    }

# ============================================================
# BIDDING STRATEGY - Celle-là sert à analyser toutes les campagnes du compte.
# ============================================================
def get_bidding_strategies(
    client: GoogleAdsClient,
    customer_id: str,
):
    """
    Retourne les stratégies d'enchères utilisées
    par toutes les campagnes du compte.
    """

    gaql = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.bidding_strategy_type,
            campaign.bidding_strategy,
            campaign.target_cpa.target_cpa_micros,
            campaign.target_roas.target_roas,
            campaign.manual_cpc.enhanced_cpc_enabled
        FROM campaign
        WHERE campaign.status != 'REMOVED'
        ORDER BY campaign.name
    """

    google_ads_service = client.get_service(
        "GoogleAdsService"
    )

    response = google_ads_service.search(
        customer_id=customer_id,
        query=gaql,
    )

    campaigns = []

    for row in response:

        target_cpa = None

        try:
            if (
                row.campaign.target_cpa
                and row.campaign.target_cpa.target_cpa_micros
            ):
                target_cpa = round(
                    row.campaign.target_cpa.target_cpa_micros
                    / 1_000_000,
                    2,
                )
        except Exception:
            pass

        target_roas = None

        try:
            if (
                row.campaign.target_roas
                and row.campaign.target_roas.target_roas
            ):
                target_roas = round(
                    float(
                        row.campaign.target_roas.target_roas
                    ),
                    2,
                )
        except Exception:
            pass

        enhanced_cpc = False

        try:
            enhanced_cpc = bool(
                row.campaign.manual_cpc
                .enhanced_cpc_enabled
            )
        except Exception:
            pass

        portfolio_strategy = None

        try:
            if row.campaign.bidding_strategy:
                portfolio_strategy = (
                    row.campaign.bidding_strategy
                )
        except Exception:
            pass

        campaigns.append(
            {
                "campaign_id": str(
                    row.campaign.id
                ),
                "campaign_name": (
                    row.campaign.name
                ),
                "status": str(
                    row.campaign.status.name
                ),
                "strategy_type": str(
                    row.campaign
                    .bidding_strategy_type
                    .name
                ),
                "target_cpa": target_cpa,
                "target_roas": target_roas,
                "portfolio_strategy": (
                    portfolio_strategy
                ),
                "enhanced_cpc": enhanced_cpc,
            }
        )

    return {
        "customer_id": customer_id,
        "campaigns_count": len(campaigns),
        "campaigns": campaigns,
    }
