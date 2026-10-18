import os
import hmac
import json
import hashlib
from typing import Dict, Any
from google.ads.googleads.client import GoogleAdsClient

from models.bidding_models import (
    AnalyzeStrategyChangeRequest,
    PreviewBiddingStrategyUpdateRequest,
    UpdateBiddingStrategyRequest,
    BiddingStrategyType,
    BiddingTargetAction,
)

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

# ============================================================
# BIDDING STRATEGY INSIGHTS - Analyse une campagne sur une période Google Ads
# ============================================================
def get_bidding_strategy_insights(
    client: GoogleAdsClient,
    customer_id: str,
    campaign_id: str,
    period: str = "LAST_30_DAYS",
):
    """
    Analyse la stratégie d'enchères actuelle d'une campagne
    et compare les objectifs configurés aux performances réelles.

    Cette fonction est strictement en lecture seule.
    Elle ne modifie aucune donnée Google Ads.
    """

    # --------------------------------------------------------
    # NORMALISATION
    # --------------------------------------------------------

    customer_id = (
        str(customer_id)
        .replace("-", "")
        .strip()
    )

    campaign_id = (
        str(campaign_id)
        .replace("-", "")
        .strip()
    )

    period = (
        str(period)
        .strip()
        .upper()
    )

    allowed_periods = {
        "TODAY",
        "YESTERDAY",
        "LAST_7_DAYS",
        "LAST_14_DAYS",
        "LAST_30_DAYS",
        "THIS_MONTH",
        "LAST_MONTH",
    }

    if period not in allowed_periods:
        raise ValueError(
            "Période invalide. Valeurs acceptées : "
            + ", ".join(
                sorted(allowed_periods)
            )
        )

    if not customer_id.isdigit():
        raise ValueError(
            "Le customer_id doit contenir uniquement "
            "des chiffres."
        )

    if not campaign_id.isdigit():
        raise ValueError(
            "Le campaign_id doit contenir uniquement "
            "des chiffres."
        )

    # --------------------------------------------------------
    # REQUÊTE GAQL
    # --------------------------------------------------------

    gaql = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
            campaign.bidding_strategy_type,
            campaign.bidding_strategy,
            campaign.bidding_strategy_system_status,

            campaign.target_cpa.target_cpa_micros,
            campaign.target_roas.target_roas,

            campaign.maximize_conversions.target_cpa_micros,
            campaign.maximize_conversion_value.target_roas,

            campaign.target_spend.cpc_bid_ceiling_micros,

            campaign.target_impression_share.location,
            campaign.target_impression_share.location_fraction_micros,
            campaign.target_impression_share.cpc_bid_ceiling_micros,

            campaign.manual_cpc.enhanced_cpc_enabled,

            metrics.impressions,
            metrics.clicks,
            metrics.ctr,
            metrics.average_cpc,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value,
            metrics.conversions_from_interactions_rate

        FROM campaign

        WHERE campaign.id = {campaign_id}
          AND campaign.status != 'REMOVED'
          AND segments.date DURING {period}

        LIMIT 1
    """

    # --------------------------------------------------------
    # EXÉCUTION
    # --------------------------------------------------------

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
            "Campagne introuvable ou aucune donnée disponible "
            f"pour la période {period}."
        )

    row = rows[0]

    campaign = row.campaign
    metrics = row.metrics

    # --------------------------------------------------------
    # INFORMATIONS DE CAMPAGNE
    # --------------------------------------------------------

    campaign_status = (
        campaign.status.name
        if hasattr(
            campaign.status,
            "name",
        )
        else str(campaign.status)
    )

    channel_type = (
        campaign.advertising_channel_type.name
        if hasattr(
            campaign.advertising_channel_type,
            "name",
        )
        else str(
            campaign.advertising_channel_type
        )
    )

    strategy_type = (
        campaign.bidding_strategy_type.name
        if hasattr(
            campaign.bidding_strategy_type,
            "name",
        )
        else str(
            campaign.bidding_strategy_type
        )
    )

    strategy_system_status = None

    try:
        strategy_system_status = (
            campaign
            .bidding_strategy_system_status
            .name
        )
    except Exception:
        try:
            strategy_system_status = str(
                campaign
                .bidding_strategy_system_status
            )
        except Exception:
            strategy_system_status = None

    # --------------------------------------------------------
    # STRATÉGIE STANDARD OU PORTEFEUILLE
    # --------------------------------------------------------

    portfolio_strategy = None
    strategy_scope = "STANDARD"

    try:
        if campaign.bidding_strategy:
            portfolio_strategy = str(
                campaign.bidding_strategy
            )

            strategy_scope = "PORTFOLIO"

    except Exception:
        portfolio_strategy = None
        strategy_scope = "STANDARD"

    # --------------------------------------------------------
    # CPA CIBLE
    # --------------------------------------------------------

    target_cpa = None
    target_cpa_source = None

    # Maximiser les conversions avec CPA cible facultatif.
    try:
        maximize_conversions_target_cpa_micros = int(
            campaign
            .maximize_conversions
            .target_cpa_micros
            or 0
        )

        if (
            maximize_conversions_target_cpa_micros
            > 0
        ):
            target_cpa = round(
                maximize_conversions_target_cpa_micros
                / 1_000_000,
                2,
            )

            target_cpa_source = (
                "MAXIMIZE_CONVERSIONS"
            )

    except Exception:
        pass

    # Ancienne configuration Target CPA.
    if target_cpa is None:

        try:
            target_cpa_micros = int(
                campaign
                .target_cpa
                .target_cpa_micros
                or 0
            )

            if target_cpa_micros > 0:
                target_cpa = round(
                    target_cpa_micros
                    / 1_000_000,
                    2,
                )

                target_cpa_source = (
                    "TARGET_CPA"
                )

        except Exception:
            pass

    # --------------------------------------------------------
    # ROAS CIBLE
    # --------------------------------------------------------

    target_roas_ratio = None
    target_roas_percent = None
    target_roas_source = None

    # Maximiser la valeur de conversion avec ROAS cible.
    try:
        maximize_value_target_roas = float(
            campaign
            .maximize_conversion_value
            .target_roas
            or 0
        )

        if maximize_value_target_roas > 0:
            target_roas_ratio = round(
                maximize_value_target_roas,
                4,
            )

            target_roas_percent = round(
                maximize_value_target_roas
                * 100,
                2,
            )

            target_roas_source = (
                "MAXIMIZE_CONVERSION_VALUE"
            )

    except Exception:
        pass

    # Ancienne configuration Target ROAS.
    if target_roas_ratio is None:

        try:
            target_roas_value = float(
                campaign
                .target_roas
                .target_roas
                or 0
            )

            if target_roas_value > 0:
                target_roas_ratio = round(
                    target_roas_value,
                    4,
                )

                target_roas_percent = round(
                    target_roas_value
                    * 100,
                    2,
                )

                target_roas_source = (
                    "TARGET_ROAS"
                )

        except Exception:
            pass

    # --------------------------------------------------------
    # MAXIMISER LES CLICS
    # --------------------------------------------------------

    cpc_bid_ceiling = None

    try:
        cpc_bid_ceiling_micros = int(
            campaign
            .target_spend
            .cpc_bid_ceiling_micros
            or 0
        )

        if cpc_bid_ceiling_micros > 0:
            cpc_bid_ceiling = round(
                cpc_bid_ceiling_micros
                / 1_000_000,
                2,
            )

    except Exception:
        pass

    # --------------------------------------------------------
    # TAUX D'IMPRESSIONS CIBLE
    # --------------------------------------------------------

    target_impression_share_percent = None
    target_impression_location = None
    target_impression_cpc_ceiling = None

    try:
        location_fraction_micros = int(
            campaign
            .target_impression_share
            .location_fraction_micros
            or 0
        )

        if location_fraction_micros > 0:
            target_impression_share_percent = round(
                (
                    location_fraction_micros
                    / 1_000_000
                )
                * 100,
                2,
            )

    except Exception:
        pass

    try:
        target_impression_location = (
            campaign
            .target_impression_share
            .location
            .name
        )

    except Exception:
        target_impression_location = None

    try:
        impression_cpc_ceiling_micros = int(
            campaign
            .target_impression_share
            .cpc_bid_ceiling_micros
            or 0
        )

        if impression_cpc_ceiling_micros > 0:
            target_impression_cpc_ceiling = round(
                impression_cpc_ceiling_micros
                / 1_000_000,
                2,
            )

    except Exception:
        pass

    # --------------------------------------------------------
    # CPC MANUEL
    # --------------------------------------------------------

    enhanced_cpc = False

    try:
        enhanced_cpc = bool(
            campaign
            .manual_cpc
            .enhanced_cpc_enabled
        )

    except Exception:
        enhanced_cpc = False

    # --------------------------------------------------------
    # MÉTRIQUES RÉELLES
    # --------------------------------------------------------

    impressions = int(
        metrics.impressions or 0
    )

    clicks = int(
        metrics.clicks or 0
    )

    cost = round(
        int(
            metrics.cost_micros or 0
        )
        / 1_000_000,
        2,
    )

    conversions = round(
        float(
            metrics.conversions or 0
        ),
        2,
    )

    conversion_value = round(
        float(
            metrics.conversions_value or 0
        ),
        2,
    )

    ctr_percent = round(
        float(
            metrics.ctr or 0
        )
        * 100,
        2,
    )

    average_cpc = round(
        int(
            metrics.average_cpc or 0
        )
        / 1_000_000,
        2,
    )

    conversion_rate_percent = round(
        float(
            metrics
            .conversions_from_interactions_rate
            or 0
        )
        * 100,
        2,
    )

    actual_cpa = (
        round(
            cost / conversions,
            2,
        )
        if conversions > 0
        else None
    )

    actual_roas_ratio = (
        round(
            conversion_value / cost,
            4,
        )
        if cost > 0
        else None
    )

    actual_roas_percent = (
        round(
            actual_roas_ratio * 100,
            2,
        )
        if actual_roas_ratio is not None
        else None
    )

    # --------------------------------------------------------
    # COMPARAISONS
    # --------------------------------------------------------

    cpa_difference = None
    cpa_difference_percent = None

    if (
        target_cpa is not None
        and actual_cpa is not None
        and target_cpa > 0
    ):
        cpa_difference = round(
            actual_cpa - target_cpa,
            2,
        )

        cpa_difference_percent = round(
            (
                (
                    actual_cpa
                    - target_cpa
                )
                / target_cpa
            )
            * 100,
            2,
        )

    roas_difference_percent = None
    roas_gap_percentage_points = None

    if (
        target_roas_percent is not None
        and actual_roas_percent is not None
        and target_roas_percent > 0
    ):
        roas_gap_percentage_points = round(
            actual_roas_percent
            - target_roas_percent,
            2,
        )

        roas_difference_percent = round(
            (
                (
                    actual_roas_percent
                    - target_roas_percent
                )
                / target_roas_percent
            )
            * 100,
            2,
        )

    # --------------------------------------------------------
    # DIAGNOSTICS
    # --------------------------------------------------------

    diagnostics = []

    if conversions <= 0:

        diagnostics.append(
            {
                "severity": "WARNING",
                "code": "NO_CONVERSIONS",
                "message": (
                    "Aucune conversion n'a été "
                    "enregistrée pendant la période."
                ),
            }
        )

    elif conversions < 15:

        diagnostics.append(
            {
                "severity": "INFO",
                "code": "LIMITED_CONVERSION_VOLUME",
                "message": (
                    "Le volume de conversions est limité. "
                    "La période contient moins de "
                    "15 conversions."
                ),
            }
        )

    else:

        diagnostics.append(
            {
                "severity": "INFO",
                "code": "SUFFICIENT_CONVERSION_VOLUME",
                "message": (
                    "La période contient au moins "
                    "15 conversions."
                ),
            }
        )

    if (
        target_cpa is not None
        and actual_cpa is not None
    ):

        if actual_cpa > target_cpa:

            diagnostics.append(
                {
                    "severity": "WARNING",
                    "code": (
                        "ACTUAL_CPA_ABOVE_TARGET"
                    ),
                    "message": (
                        "Le CPA réel est supérieur "
                        "au CPA cible."
                    ),
                    "target_cpa": target_cpa,
                    "actual_cpa": actual_cpa,
                    "difference_percent": (
                        cpa_difference_percent
                    ),
                }
            )

        elif actual_cpa < target_cpa:

            diagnostics.append(
                {
                    "severity": "POSITIVE",
                    "code": (
                        "ACTUAL_CPA_BELOW_TARGET"
                    ),
                    "message": (
                        "Le CPA réel est inférieur "
                        "au CPA cible."
                    ),
                    "target_cpa": target_cpa,
                    "actual_cpa": actual_cpa,
                    "difference_percent": (
                        cpa_difference_percent
                    ),
                }
            )

        else:

            diagnostics.append(
                {
                    "severity": "INFO",
                    "code": (
                        "ACTUAL_CPA_MATCHES_TARGET"
                    ),
                    "message": (
                        "Le CPA réel correspond "
                        "au CPA cible."
                    ),
                }
            )

    if (
        target_roas_percent is not None
        and actual_roas_percent is not None
    ):

        if (
            actual_roas_percent
            < target_roas_percent
        ):

            diagnostics.append(
                {
                    "severity": "WARNING",
                    "code": (
                        "ACTUAL_ROAS_BELOW_TARGET"
                    ),
                    "message": (
                        "Le ROAS réel est inférieur "
                        "au ROAS cible."
                    ),
                    "target_roas_percent": (
                        target_roas_percent
                    ),
                    "actual_roas_percent": (
                        actual_roas_percent
                    ),
                    "difference_percent": (
                        roas_difference_percent
                    ),
                }
            )

        elif (
            actual_roas_percent
            > target_roas_percent
        ):

            diagnostics.append(
                {
                    "severity": "POSITIVE",
                    "code": (
                        "ACTUAL_ROAS_ABOVE_TARGET"
                    ),
                    "message": (
                        "Le ROAS réel est supérieur "
                        "au ROAS cible."
                    ),
                    "target_roas_percent": (
                        target_roas_percent
                    ),
                    "actual_roas_percent": (
                        actual_roas_percent
                    ),
                    "difference_percent": (
                        roas_difference_percent
                    ),
                }
            )

        else:

            diagnostics.append(
                {
                    "severity": "INFO",
                    "code": (
                        "ACTUAL_ROAS_MATCHES_TARGET"
                    ),
                    "message": (
                        "Le ROAS réel correspond "
                        "au ROAS cible."
                    ),
                }
            )

    # --------------------------------------------------------
    # DESCRIPTION DE LA STRATÉGIE ACTUELLE
    # --------------------------------------------------------

    strategy_description = (
        f"La campagne utilise la stratégie "
        f"{strategy_type}."
    )

    if (
        strategy_type
        == "MAXIMIZE_CONVERSIONS"
    ):

        if target_cpa is None:
            strategy_description = (
                "La campagne utilise Maximiser les "
                "conversions sans CPA cible."
            )
        else:
            strategy_description = (
                "La campagne utilise Maximiser les "
                "conversions avec un CPA cible de "
                f"{target_cpa}."
            )

    elif (
        strategy_type
        == "MAXIMIZE_CONVERSION_VALUE"
    ):

        if target_roas_percent is None:
            strategy_description = (
                "La campagne utilise Maximiser la "
                "valeur de conversion sans ROAS cible."
            )
        else:
            strategy_description = (
                "La campagne utilise Maximiser la "
                "valeur de conversion avec un ROAS "
                f"cible de {target_roas_percent} %."
            )

    elif strategy_type == "TARGET_CPA":

        strategy_description = (
            "La campagne utilise une stratégie "
            f"CPA cible de {target_cpa}."
        )

    elif strategy_type == "TARGET_ROAS":

        strategy_description = (
            "La campagne utilise une stratégie "
            f"ROAS cible de {target_roas_percent} %."
        )

    elif strategy_type == "TARGET_SPEND":

        strategy_description = (
            "La campagne utilise Maximiser les clics."
        )

        if cpc_bid_ceiling is not None:
            strategy_description += (
                " La limite d'enchère CPC est de "
                f"{cpc_bid_ceiling}."
            )

    elif strategy_type == "MANUAL_CPC":

        strategy_description = (
            "La campagne utilise le CPC manuel."
        )

    elif (
        strategy_type
        == "TARGET_IMPRESSION_SHARE"
    ):

        strategy_description = (
            "La campagne utilise le taux "
            "d'impressions cible."
        )

    # --------------------------------------------------------
    # RÉPONSE
    # --------------------------------------------------------

    return {
        "customer_id": customer_id,

        "campaign_id": str(
            campaign.id
        ),

        "campaign_name": (
            campaign.name
        ),

        "campaign_status": (
            campaign_status
        ),

        "channel_type": (
            channel_type
        ),

        "period": period,

        "strategy": {
            "scope": strategy_scope,
            "strategy_type": strategy_type,
            "system_status": (
                strategy_system_status
            ),
            "description": (
                strategy_description
            ),
            "portfolio_strategy": (
                portfolio_strategy
            ),
            "target_cpa": target_cpa,
            "target_cpa_source": (
                target_cpa_source
            ),
            "target_roas_ratio": (
                target_roas_ratio
            ),
            "target_roas_percent": (
                target_roas_percent
            ),
            "target_roas_source": (
                target_roas_source
            ),
            "cpc_bid_ceiling": (
                cpc_bid_ceiling
            ),
            "enhanced_cpc": (
                enhanced_cpc
            ),
            "target_impression_share": {
                "percentage": (
                    target_impression_share_percent
                ),
                "location": (
                    target_impression_location
                ),
                "cpc_bid_ceiling": (
                    target_impression_cpc_ceiling
                ),
            },
        },

        "performance": {
            "impressions": impressions,
            "clicks": clicks,
            "ctr_percent": (
                ctr_percent
            ),
            "average_cpc": (
                average_cpc
            ),
            "cost": cost,
            "conversions": (
                conversions
            ),
            "conversion_rate_percent": (
                conversion_rate_percent
            ),
            "conversion_value": (
                conversion_value
            ),
            "actual_cpa": (
                actual_cpa
            ),
            "actual_roas_ratio": (
                actual_roas_ratio
            ),
            "actual_roas_percent": (
                actual_roas_percent
            ),
        },

        "target_comparison": {
            "cpa": {
                "target": target_cpa,
                "actual": actual_cpa,
                "difference": (
                    cpa_difference
                ),
                "difference_percent": (
                    cpa_difference_percent
                ),
            },
            "roas": {
                "target_percent": (
                    target_roas_percent
                ),
                "actual_percent": (
                    actual_roas_percent
                ),
                "gap_percentage_points": (
                    roas_gap_percentage_points
                ),
                "difference_percent": (
                    roas_difference_percent
                ),
            },
        },

        "diagnostics": diagnostics,

        "modification_applied": False,

        "confirmation_required": False,
    }

# ============================================================
# ANALYZE BIDDING STRATEGY CHANGE
# ============================================================
def analyze_strategy_change(
    client: GoogleAdsClient,
    request: AnalyzeStrategyChangeRequest,
):
    """
    Analyse une modification potentielle de stratégie
    d'enchères sans modifier Google Ads.

    La fonction :
    - lit la configuration actuelle ;
    - analyse les performances ;
    - normalise la demande ;
    - vérifie les paramètres nécessaires ;
    - retourne une recommandation ;
    - prépare une configuration proposée.

    Aucune mutation Google Ads n'est effectuée.
    """

    # --------------------------------------------------------
    # NORMALISATION
    # --------------------------------------------------------

    customer_id = (
        str(request.customer_id)
        .replace("-", "")
        .strip()
    )

    campaign_id = (
        str(request.campaign_id)
        .replace("-", "")
        .strip()
    )

    period = (
        str(request.period)
        .strip()
        .upper()
    )

    requested_strategy_type = (
        request.requested_strategy_type.value
    )

    target_action = (
        request.target_action.value
    )

    if not customer_id.isdigit():
        raise ValueError(
            "Le customer_id doit contenir "
            "uniquement des chiffres."
        )

    if not campaign_id.isdigit():
        raise ValueError(
            "Le campaign_id doit contenir "
            "uniquement des chiffres."
        )

    # --------------------------------------------------------
    # ANALYSE DE LA STRATÉGIE ACTUELLE
    # --------------------------------------------------------

    current_analysis = (
        get_bidding_strategy_insights(
            client=client,
            customer_id=customer_id,
            campaign_id=campaign_id,
            period=period,
        )
    )

    campaign_name = (
        current_analysis["campaign_name"]
    )

    campaign_status = (
        current_analysis["campaign_status"]
    )

    channel_type = (
        current_analysis["channel_type"]
    )

    current_strategy = (
        current_analysis["strategy"]
    )

    performance = (
        current_analysis["performance"]
    )

    current_strategy_type = (
        current_strategy["strategy_type"]
    )

    current_target_cpa = (
        current_strategy["target_cpa"]
    )

    current_target_roas_percent = (
        current_strategy[
            "target_roas_percent"
        ]
    )

    current_cpc_bid_ceiling = (
        current_strategy[
            "cpc_bid_ceiling"
        ]
    )

    actual_cpa = (
        performance["actual_cpa"]
    )

    actual_roas_percent = (
        performance[
            "actual_roas_percent"
        ]
    )

    conversions = float(
        performance["conversions"] or 0
    )

    cost = float(
        performance["cost"] or 0
    )

    # --------------------------------------------------------
    # VARIABLES DE RÉPONSE
    # --------------------------------------------------------

    errors = []
    warnings = []
    observations = []
    recommendations = []

    compatible = True

    proposed_target_cpa = None
    proposed_target_roas_percent = None
    proposed_cpc_bid_ceiling = None

    proposed_impression_share_percent = None
    proposed_impression_location = None

    # --------------------------------------------------------
    # CONTRÔLES GÉNÉRAUX
    # --------------------------------------------------------

    if campaign_status == "REMOVED":
        compatible = False

        errors.append(
            {
                "code": "CAMPAIGN_REMOVED",
                "message": (
                    "Une campagne supprimée ne peut "
                    "pas recevoir une nouvelle "
                    "stratégie d'enchères."
                ),
            }
        )

    if campaign_status == "PAUSED":
        warnings.append(
            {
                "code": "CAMPAIGN_PAUSED",
                "message": (
                    "La campagne est actuellement "
                    "en pause. La stratégie peut être "
                    "analysée, mais son impact ne sera "
                    "pas observable tant que la "
                    "campagne restera en pause."
                ),
            }
        )

    if cost <= 0:
        warnings.append(
            {
                "code": "NO_COST_IN_PERIOD",
                "message": (
                    "Aucune dépense n'a été "
                    "enregistrée pendant la période."
                ),
            }
        )

    if conversions <= 0:
        warnings.append(
            {
                "code": "NO_CONVERSIONS_IN_PERIOD",
                "message": (
                    "Aucune conversion n'a été "
                    "enregistrée pendant la période."
                ),
            }
        )

    elif conversions < 15:
        warnings.append(
            {
                "code": "LIMITED_CONVERSION_VOLUME",
                "message": (
                    "Le volume de conversions est "
                    "limité pour la période analysée."
                ),
                "conversions": conversions,
            }
        )

    else:
        observations.append(
            {
                "code": (
                    "SUFFICIENT_CONVERSION_VOLUME"
                ),
                "message": (
                    "La période contient un volume "
                    "de conversions exploitable pour "
                    "l'analyse."
                ),
                "conversions": conversions,
            }
        )

    # --------------------------------------------------------
    # MAXIMISER LES CONVERSIONS
    # --------------------------------------------------------

    if (
        requested_strategy_type
        == BiddingStrategyType
        .MAXIMIZE_CONVERSIONS
        .value
    ):
        if target_action == "SET":

            if request.target_cpa is None:
                compatible = False

                errors.append(
                    {
                        "code": (
                            "TARGET_CPA_REQUIRED"
                        ),
                        "message": (
                            "Un CPA cible est requis "
                            "quand target_action vaut "
                            "SET."
                        ),
                    }
                )

            else:
                proposed_target_cpa = round(
                    request.target_cpa,
                    2,
                )

        elif target_action == "REMOVE":

            proposed_target_cpa = None
            
            if current_target_cpa is not None:

                warnings.append(
                    {
                        "code": (
                            "TARGET_CPA_REMOVAL_IMPACT"
                        ),
                        "message": (
                            "La suppression du CPA cible "
                            "donnera davantage de liberté "
                            "à Maximiser les conversions. "
                            "Les dépenses et le CPA réel "
                            "pourraient augmenter."
                        ),
                        "current_target_cpa": (
                            current_target_cpa
                        ),
                        "actual_cpa": actual_cpa,
                    }
                )

            if (
                current_strategy.get(
                    "system_status"
                )
                == "LIMITED_BY_BUDGET"
            ):

                warnings.append(
                    {
                        "code": (
                            "CAMPAIGN_LIMITED_BY_BUDGET"
                        ),
                        "message": (
                            "La campagne est limitée par "
                            "le budget. La suppression du "
                            "CPA cible pourrait augmenter "
                            "la consommation du budget."
                        ),
                    }
                )

            observations.append(
                {
                    "code": "TARGET_CPA_REMOVED",
                    "message": (
                        "La proposition utilise "
                        "Maximiser les conversions "
                        "sans CPA cible."
                    ),
                }
            )

        elif target_action in {
            "INCREASE_PERCENT",
            "DECREASE_PERCENT",
        }:

            if current_target_cpa is None:
                compatible = False

                errors.append(
                    {
                        "code": (
                            "CURRENT_TARGET_CPA_MISSING"
                        ),
                        "message": (
                            "La campagne ne possède "
                            "aucun CPA cible à modifier."
                        ),
                    }
                )

            elif request.change_percent is None:
                compatible = False

                errors.append(
                    {
                        "code": (
                            "CHANGE_PERCENT_REQUIRED"
                        ),
                        "message": (
                            "Le pourcentage de "
                            "modification est requis."
                        ),
                    }
                )

            else:
                multiplier = (
                    1
                    + request.change_percent / 100
                    if target_action
                    == "INCREASE_PERCENT"
                    else
                    1
                    - request.change_percent / 100
                )

                proposed_target_cpa = round(
                    current_target_cpa
                    * multiplier,
                    2,
                )

                if proposed_target_cpa <= 0:
                    compatible = False

                    errors.append(
                        {
                            "code": (
                                "INVALID_TARGET_CPA"
                            ),
                            "message": (
                                "Le CPA cible calculé "
                                "doit être supérieur "
                                "à zéro."
                            ),
                        }
                    )

        else:
            proposed_target_cpa = (
                current_target_cpa
                if current_strategy_type
                == "MAXIMIZE_CONVERSIONS"
                else None
            )

        if (
            proposed_target_cpa is not None
            and actual_cpa is not None
        ):
            target_vs_actual_percent = round(
                (
                    (
                        proposed_target_cpa
                        - actual_cpa
                    )
                    / actual_cpa
                )
                * 100,
                2,
            )

            if (
                proposed_target_cpa
                < actual_cpa * 0.80
            ):
                warnings.append(
                    {
                        "code": (
                            "TARGET_CPA_MUCH_LOWER_"
                            "THAN_ACTUAL"
                        ),
                        "message": (
                            "Le CPA cible proposé est "
                            "nettement inférieur au CPA "
                            "réel observé. Cette cible "
                            "pourrait limiter le volume."
                        ),
                        "actual_cpa": actual_cpa,
                        "proposed_target_cpa": (
                            proposed_target_cpa
                        ),
                        "difference_percent": (
                            target_vs_actual_percent
                        ),
                    }
                )

            elif (
                proposed_target_cpa
                > actual_cpa * 1.50
            ):
                warnings.append(
                    {
                        "code": (
                            "TARGET_CPA_MUCH_HIGHER_"
                            "THAN_ACTUAL"
                        ),
                        "message": (
                            "Le CPA cible proposé est "
                            "nettement supérieur au CPA "
                            "réel observé. Google Ads "
                            "pourrait accepter un coût "
                            "par conversion plus élevé."
                        ),
                        "actual_cpa": actual_cpa,
                        "proposed_target_cpa": (
                            proposed_target_cpa
                        ),
                        "difference_percent": (
                            target_vs_actual_percent
                        ),
                    }
                )

            else:
                observations.append(
                    {
                        "code": (
                            "TARGET_CPA_NEAR_ACTUAL"
                        ),
                        "message": (
                            "Le CPA cible proposé reste "
                            "dans une plage relativement "
                            "proche du CPA observé."
                        ),
                    }
                )

        if (
            request.target_cpa is None
            and target_action == "KEEP"
            and current_strategy_type
            != "MAXIMIZE_CONVERSIONS"
        ):
            recommendations.append(
                {
                    "code": (
                        "START_WITHOUT_TARGET_CPA"
                    ),
                    "message": (
                        "La stratégie peut être "
                        "démarrée sans CPA cible, puis "
                        "réévaluée après observation "
                        "des performances."
                    ),
                }
            )

    # --------------------------------------------------------
    # MAXIMISER LA VALEUR DE CONVERSION
    # --------------------------------------------------------

    elif (
        requested_strategy_type
        == BiddingStrategyType
        .MAXIMIZE_CONVERSION_VALUE
        .value
    ):
        if target_action == "SET":

            if (
                request.target_roas_percent
                is None
            ):
                compatible = False

                errors.append(
                    {
                        "code": (
                            "TARGET_ROAS_REQUIRED"
                        ),
                        "message": (
                            "Un ROAS cible est requis "
                            "quand target_action vaut "
                            "SET."
                        ),
                    }
                )

            else:
                proposed_target_roas_percent = round(
                    request.target_roas_percent,
                    2,
                )

        elif target_action == "REMOVE":

            proposed_target_roas_percent = None

            observations.append(
                {
                    "code": "TARGET_ROAS_REMOVED",
                    "message": (
                        "La proposition utilise "
                        "Maximiser la valeur de "
                        "conversion sans ROAS cible."
                    ),
                }
            )

        elif target_action in {
            "INCREASE_PERCENT",
            "DECREASE_PERCENT",
        }:

            if (
                current_target_roas_percent
                is None
            ):
                compatible = False

                errors.append(
                    {
                        "code": (
                            "CURRENT_TARGET_ROAS_MISSING"
                        ),
                        "message": (
                            "La campagne ne possède "
                            "aucun ROAS cible à modifier."
                        ),
                    }
                )

            elif request.change_percent is None:
                compatible = False

                errors.append(
                    {
                        "code": (
                            "CHANGE_PERCENT_REQUIRED"
                        ),
                        "message": (
                            "Le pourcentage de "
                            "modification est requis."
                        ),
                    }
                )

            else:
                multiplier = (
                    1
                    + request.change_percent / 100
                    if target_action
                    == "INCREASE_PERCENT"
                    else
                    1
                    - request.change_percent / 100
                )

                proposed_target_roas_percent = round(
                    current_target_roas_percent
                    * multiplier,
                    2,
                )

                if (
                    proposed_target_roas_percent
                    <= 0
                ):
                    compatible = False

                    errors.append(
                        {
                            "code": (
                                "INVALID_TARGET_ROAS"
                            ),
                            "message": (
                                "Le ROAS cible calculé "
                                "doit être supérieur "
                                "à zéro."
                            ),
                        }
                    )

        else:
            proposed_target_roas_percent = (
                current_target_roas_percent
                if current_strategy_type
                == "MAXIMIZE_CONVERSION_VALUE"
                else None
            )

        if (
            proposed_target_roas_percent
            is not None
            and actual_roas_percent is not None
        ):
            if (
                proposed_target_roas_percent
                > actual_roas_percent * 1.30
            ):
                warnings.append(
                    {
                        "code": (
                            "TARGET_ROAS_MUCH_HIGHER_"
                            "THAN_ACTUAL"
                        ),
                        "message": (
                            "Le ROAS cible proposé est "
                            "nettement supérieur au ROAS "
                            "réel. Cette cible pourrait "
                            "limiter le volume ou les "
                            "dépenses."
                        ),
                        "actual_roas_percent": (
                            actual_roas_percent
                        ),
                        "proposed_target_roas_percent": (
                            proposed_target_roas_percent
                        ),
                    }
                )

            elif (
                proposed_target_roas_percent
                < actual_roas_percent * 0.50
            ):
                warnings.append(
                    {
                        "code": (
                            "TARGET_ROAS_MUCH_LOWER_"
                            "THAN_ACTUAL"
                        ),
                        "message": (
                            "Le ROAS cible proposé est "
                            "nettement inférieur au ROAS "
                            "réel. La stratégie pourrait "
                            "privilégier davantage de "
                            "volume au détriment de "
                            "l'efficacité observée."
                        ),
                        "actual_roas_percent": (
                            actual_roas_percent
                        ),
                        "proposed_target_roas_percent": (
                            proposed_target_roas_percent
                        ),
                    }
                )

            else:
                observations.append(
                    {
                        "code": (
                            "TARGET_ROAS_NEAR_ACTUAL"
                        ),
                        "message": (
                            "Le ROAS cible proposé reste "
                            "dans une plage relativement "
                            "proche du ROAS observé."
                        ),
                    }
                )

        if conversion_value <= 0:
            warnings.append(
                {
                    "code": (
                        "NO_CONVERSION_VALUE"
                    ),
                    "message": (
                        "Aucune valeur de conversion "
                        "positive n'a été trouvée. "
                        "Maximiser la valeur de "
                        "conversion pourrait ne pas "
                        "disposer du signal requis."
                    ),
                }
            )

    # --------------------------------------------------------
    # MAXIMISER LES CLICS
    # --------------------------------------------------------

    elif (
        requested_strategy_type
        == BiddingStrategyType
        .MAXIMIZE_CLICKS
        .value
    ):
        if target_action == "SET":

            if request.cpc_bid_ceiling is None:
                compatible = False

                errors.append(
                    {
                        "code": (
                            "CPC_BID_CEILING_REQUIRED"
                        ),
                        "message": (
                            "Une limite CPC maximale est "
                            "requise quand target_action "
                            "vaut SET."
                        ),
                    }
                )

            else:
                proposed_cpc_bid_ceiling = round(
                    request.cpc_bid_ceiling,
                    2,
                )

        elif target_action == "REMOVE":

            proposed_cpc_bid_ceiling = None

            observations.append(
                {
                    "code": (
                        "CPC_BID_CEILING_REMOVED"
                    ),
                    "message": (
                        "La proposition utilise "
                        "Maximiser les clics sans "
                        "limite CPC maximale."
                    ),
                }
            )

        elif target_action == "KEEP":

            proposed_cpc_bid_ceiling = (
                current_cpc_bid_ceiling
                if current_strategy_type
                == "TARGET_SPEND"
                else None
            )

        if (
            proposed_cpc_bid_ceiling is not None
            and performance["average_cpc"] > 0
        ):
            if (
                proposed_cpc_bid_ceiling
                < performance["average_cpc"]
            ):
                warnings.append(
                    {
                        "code": (
                            "CPC_CEILING_BELOW_"
                            "AVERAGE_CPC"
                        ),
                        "message": (
                            "La limite CPC proposée est "
                            "inférieure au CPC moyen "
                            "observé. Cette limite peut "
                            "réduire la capacité à "
                            "obtenir des clics."
                        ),
                        "average_cpc": (
                            performance["average_cpc"]
                        ),
                        "proposed_cpc_bid_ceiling": (
                            proposed_cpc_bid_ceiling
                        ),
                    }
                )

    # --------------------------------------------------------
    # CPC MANUEL
    # --------------------------------------------------------

    elif (
        requested_strategy_type
        == BiddingStrategyType
        .MANUAL_CPC
        .value
    ):
        if channel_type != "SEARCH":

            warnings.append(
                {
                    "code": (
                        "MANUAL_CPC_CHANNEL_REVIEW"
                    ),
                    "message": (
                        "La compatibilité du CPC manuel "
                        "doit être vérifiée pour ce type "
                        "de campagne."
                    ),
                    "channel_type": channel_type,
                }
            )

        observations.append(
            {
                "code": (
                    "AD_GROUP_CPC_REQUIRED"
                ),
                "message": (
                    "Le passage au CPC manuel ne fixe "
                    "pas automatiquement une enchère "
                    "unique pour tous les groupes "
                    "d'annonces. Les enchères CPC des "
                    "groupes devront être analysées "
                    "séparément."
                ),
            }
        )

        if request.cpc_bid_ceiling is not None:

            proposed_cpc_bid_ceiling = round(
                request.cpc_bid_ceiling,
                2,
            )

            recommendations.append(
                {
                    "code": (
                        "USE_AD_GROUP_CPC_UPDATE"
                    ),
                    "message": (
                        "Après le changement de "
                        "stratégie, utilisez l'action "
                        "de mise à jour des enchères "
                        "CPC des groupes d'annonces."
                    ),
                }
            )

    # --------------------------------------------------------
    # TAUX D'IMPRESSIONS CIBLE
    # --------------------------------------------------------

    elif (
        requested_strategy_type
        == BiddingStrategyType
        .TARGET_IMPRESSION_SHARE
        .value
    ):
        if (
            request
            .target_impression_share_percent
            is None
        ):
            compatible = False

            errors.append(
                {
                    "code": (
                        "IMPRESSION_SHARE_REQUIRED"
                    ),
                    "message": (
                        "La part d'impressions cible "
                        "est obligatoire."
                    ),
                }
            )

        else:
            proposed_impression_share_percent = (
                round(
                    request
                    .target_impression_share_percent,
                    2,
                )
            )

        if (
            request.target_impression_location
            is None
        ):
            compatible = False

            errors.append(
                {
                    "code": (
                        "IMPRESSION_LOCATION_REQUIRED"
                    ),
                    "message": (
                        "L'emplacement cible est "
                        "obligatoire : "
                        "ANYWHERE_ON_PAGE, TOP_OF_PAGE "
                        "ou ABSOLUTE_TOP_OF_PAGE."
                    ),
                }
            )

        else:
            proposed_impression_location = (
                request
                .target_impression_location
                .value
            )

        if request.cpc_bid_ceiling is None:
            compatible = False

            errors.append(
                {
                    "code": (
                        "CPC_BID_CEILING_REQUIRED"
                    ),
                    "message": (
                        "Une limite CPC maximale est "
                        "requise pour préparer cette "
                        "stratégie."
                    ),
                }
            )

        else:
            proposed_cpc_bid_ceiling = round(
                request.cpc_bid_ceiling,
                2,
            )

        if channel_type != "SEARCH":
            compatible = False

            errors.append(
                {
                    "code": (
                        "TARGET_IMPRESSION_SHARE_"
                        "SEARCH_ONLY"
                    ),
                    "message": (
                        "Cette première version limite "
                        "le Taux d'impressions cible "
                        "aux campagnes Search."
                    ),
                }
            )

    # --------------------------------------------------------
    # STRATÉGIE NON SUPPORTÉE
    # --------------------------------------------------------

    else:
        compatible = False

        errors.append(
            {
                "code": (
                    "UNSUPPORTED_STRATEGY"
                ),
                "message": (
                    "La stratégie demandée n'est pas "
                    "prise en charge par cette version."
                ),
            }
        )

    # --------------------------------------------------------
    # RISQUE GÉNÉRAL
    # --------------------------------------------------------

    risk_level = "LOW"

    if errors:
        risk_level = "BLOCKED"

    elif len(warnings) >= 3:
        risk_level = "HIGH"

    elif warnings:
        risk_level = "MEDIUM"

    # --------------------------------------------------------
    # RÉSUMÉ LISIBLE PAR COPILOT
    # --------------------------------------------------------

    summary = (
        f"La campagne {campaign_name} utilise "
        f"actuellement {current_strategy_type}. "
        f"La stratégie demandée est "
        f"{requested_strategy_type}."
    )

    if compatible:
        summary += (
            " La demande est prête à être "
            "prévisualisée, mais aucune modification "
            "n'a été appliquée."
        )
    else:
        summary += (
            " La demande ne peut pas être "
            "prévisualisée tant que les erreurs "
            "indiquées ne sont pas corrigées."
        )

    # --------------------------------------------------------
    # CONFIGURATION PROPOSÉE
    # --------------------------------------------------------

    proposed_configuration = {
        "strategy_type": (
            requested_strategy_type
        ),

        "target_action": target_action,

        "target_cpa": (
            proposed_target_cpa
        ),

        "target_roas_percent": (
            proposed_target_roas_percent
        ),

        "target_roas_ratio": (
            round(
                proposed_target_roas_percent
                / 100,
                4,
            )
            if proposed_target_roas_percent
            is not None
            else None
        ),

        "cpc_bid_ceiling": (
            proposed_cpc_bid_ceiling
        ),

        "target_impression_share_percent": (
            proposed_impression_share_percent
        ),

        "target_impression_location": (
            proposed_impression_location
        ),
    }

    # --------------------------------------------------------
    # RÉPONSE
    # --------------------------------------------------------

    return {
        "customer_id": customer_id,

        "campaign_id": campaign_id,

        "campaign_name": campaign_name,

        "campaign_status": campaign_status,

        "channel_type": channel_type,

        "period": period,

        "analysis_status": (
            "READY_FOR_PREVIEW"
            if compatible
            else "BLOCKED"
        ),

        "compatible": compatible,

        "current_configuration": {
            "strategy_scope": (
                current_strategy["scope"]
            ),

            "strategy_type": (
                current_strategy_type
            ),

            "system_status": (
                current_strategy[
                    "system_status"
                ]
            ),

            "target_cpa": (
                current_target_cpa
            ),

            "target_roas_percent": (
                current_target_roas_percent
            ),

            "cpc_bid_ceiling": (
                current_cpc_bid_ceiling
            ),

            "portfolio_strategy": (
                current_strategy[
                    "portfolio_strategy"
                ]
            ),
        },

        "performance": performance,

        "requested_change": {
            "requested_strategy_type": (
                requested_strategy_type
            ),

            "target_action": target_action,

            "requested_target_cpa": (
                request.target_cpa
            ),

            "requested_target_roas_percent": (
                request
                .target_roas_percent
            ),

            "requested_cpc_bid_ceiling": (
                request.cpc_bid_ceiling
            ),

            "requested_change_percent": (
                request.change_percent
            ),

            "requested_impression_share_percent": (
                request
                .target_impression_share_percent
            ),

            "requested_impression_location": (
                request
                .target_impression_location
                .value
                if request
                .target_impression_location
                is not None
                else None
            ),

            "reason": request.reason,
        },

        "proposed_configuration": (
            proposed_configuration
        ),

        "risk_level": risk_level,

        "errors": errors,

        "warnings": warnings,

        "observations": observations,

        "recommendations": recommendations,

        "summary": summary,

        "modification_applied": False,

        "confirmation_required": (
            compatible
        ),

        "next_action": (
            "PREVIEW_BIDDING_STRATEGY_UPDATE"
            if compatible
            else "CORRECT_REQUEST"
        ),
    }

# ============================================================
# PREVIEW BIDDING STRATEGY UPDATE
# ============================================================
def preview_bidding_strategy_update(
    client: GoogleAdsClient,
    request: PreviewBiddingStrategyUpdateRequest,
):
    """
    Prévisualise une modification de stratégie
    d'enchères sans modifier Google Ads.

    La fonction :
    - relit la campagne dans Google Ads ;
    - exécute l'analyse de compatibilité ;
    - compare l'ancienne et la nouvelle configuration ;
    - calcule les variations ;
    - retourne un résumé prêt à présenter dans Copilot.

    Aucun code de confirmation n'est demandé ici,
    car aucune mutation n'est effectuée.
    """

    # --------------------------------------------------------
    # REUTILISATION DE L'ANALYSE
    # --------------------------------------------------------

    analysis_request = (
        AnalyzeStrategyChangeRequest(
            **request.model_dump()
        )
    )

    analysis = analyze_strategy_change(
        client=client,
        request=analysis_request,
    )

    # --------------------------------------------------------
    # VERIFICATION DE L'ANALYSE
    # --------------------------------------------------------

    if not analysis.get(
        "compatible",
        False,
    ):
        return {
            "customer_id": analysis.get(
                "customer_id"
            ),

            "campaign_id": analysis.get(
                "campaign_id"
            ),

            "campaign_name": analysis.get(
                "campaign_name"
            ),

            "preview_status": "BLOCKED",

            "compatible": False,

            "errors": analysis.get(
                "errors",
                [],
            ),

            "warnings": analysis.get(
                "warnings",
                [],
            ),

            "observations": analysis.get(
                "observations",
                [],
            ),

            "recommendations": analysis.get(
                "recommendations",
                [],
            ),

            "modification_applied": False,

            "confirmation_required": False,

            "next_action": "CORRECT_REQUEST",

            "message": (
                "La modification ne peut pas être "
                "prévisualisée tant que les erreurs "
                "indiquées ne sont pas corrigées."
            ),
        }

    # --------------------------------------------------------
    # CONFIGURATIONS
    # --------------------------------------------------------

    current_configuration = (
        analysis["current_configuration"]
    )

    proposed_configuration = (
        analysis["proposed_configuration"]
    )

    current_strategy_type = (
        current_configuration.get(
            "strategy_type"
        )
    )

    proposed_strategy_type = (
        proposed_configuration.get(
            "strategy_type"
        )
    )

    current_target_cpa = (
        current_configuration.get(
            "target_cpa"
        )
    )

    proposed_target_cpa = (
        proposed_configuration.get(
            "target_cpa"
        )
    )

    current_target_roas_percent = (
        current_configuration.get(
            "target_roas_percent"
        )
    )

    proposed_target_roas_percent = (
        proposed_configuration.get(
            "target_roas_percent"
        )
    )

    current_cpc_bid_ceiling = (
        current_configuration.get(
            "cpc_bid_ceiling"
        )
    )

    proposed_cpc_bid_ceiling = (
        proposed_configuration.get(
            "cpc_bid_ceiling"
        )
    )

    current_impression_share = (
        current_configuration.get(
            "target_impression_share_percent"
        )
    )

    proposed_impression_share = (
        proposed_configuration.get(
            "target_impression_share_percent"
        )
    )

    current_impression_location = (
        current_configuration.get(
            "target_impression_location"
        )
    )

    proposed_impression_location = (
        proposed_configuration.get(
            "target_impression_location"
        )
    )

    # --------------------------------------------------------
    # FONCTIONS INTERNES DE COMPARAISON
    # --------------------------------------------------------

    def calculate_difference(
        old_value,
        new_value,
    ):
        """
        Calcule la différence uniquement lorsque
        les deux valeurs sont numériques.

        Pour les chaînes de caractères comme
        MAXIMIZE_CONVERSIONS ou MANUAL_CPC,
        aucune différence numérique n'est calculée.
        """

        if (
            old_value is None
            or new_value is None
        ):
            return {
                "difference": None,
                "difference_percent": None,
            }

        try:
            old_number = float(
                old_value
            )

            new_number = float(
                new_value
            )

        except (
            TypeError,
            ValueError,
        ):
            return {
                "difference": None,
                "difference_percent": None,
            }

        difference = round(
            new_number - old_number,
            2,
        )

        difference_percent = None

        if old_number != 0:
            difference_percent = round(
                (
                    difference
                    / abs(old_number)
                )
                * 100,
                2,
            )

        return {
            "difference": difference,
            "difference_percent": (
                difference_percent
            ),
        }


    def add_change(
        changes,
        field_name,
        field_label,
        old_value,
        new_value,
        unit=None,
    ):
        """
        Ajoute un changement seulement si
        l'ancienne et la nouvelle valeur diffèrent.
        """

        if old_value == new_value:
            return

        difference_data = (
            calculate_difference(
                old_value,
                new_value,
            )
        )

        if (
            old_value is None
            and new_value is not None
        ):
            change_type = "ADDED"

        elif (
            old_value is not None
            and new_value is None
        ):
            change_type = "REMOVED"

        else:
            change_type = "UPDATED"

        changes.append(
            {
                "field": field_name,

                "label": field_label,

                "change_type": (
                    change_type
                ),

                "old_value": old_value,

                "new_value": new_value,

                "unit": unit,

                "difference": (
                    difference_data[
                        "difference"
                    ]
                ),

                "difference_percent": (
                    difference_data[
                        "difference_percent"
                    ]
                ),
            }
        )

    # --------------------------------------------------------
    # CONSTRUCTION DE LA LISTE DES CHANGEMENTS
    # --------------------------------------------------------

    changes = []

    add_change(
        changes=changes,
        field_name="strategy_type",
        field_label="Stratégie d'enchères",
        old_value=current_strategy_type,
        new_value=proposed_strategy_type,
    )

    add_change(
        changes=changes,
        field_name="target_cpa",
        field_label="CPA cible",
        old_value=current_target_cpa,
        new_value=proposed_target_cpa,
        unit="ACCOUNT_CURRENCY",
    )

    add_change(
        changes=changes,
        field_name="target_roas_percent",
        field_label="ROAS cible",
        old_value=(
            current_target_roas_percent
        ),
        new_value=(
            proposed_target_roas_percent
        ),
        unit="PERCENT",
    )

    add_change(
        changes=changes,
        field_name="cpc_bid_ceiling",
        field_label="Limite CPC maximale",
        old_value=(
            current_cpc_bid_ceiling
        ),
        new_value=(
            proposed_cpc_bid_ceiling
        ),
        unit="ACCOUNT_CURRENCY",
    )

    add_change(
        changes=changes,
        field_name=(
            "target_impression_share_percent"
        ),
        field_label=(
            "Part d'impressions cible"
        ),
        old_value=(
            current_impression_share
        ),
        new_value=(
            proposed_impression_share
        ),
        unit="PERCENT",
    )

    add_change(
        changes=changes,
        field_name=(
            "target_impression_location"
        ),
        field_label=(
            "Emplacement d'impression cible"
        ),
        old_value=(
            current_impression_location
        ),
        new_value=(
            proposed_impression_location
        ),
    )

    # --------------------------------------------------------
    # IDENTIFICATION DES CHANGEMENTS SENSIBLES
    # --------------------------------------------------------

    sensitive_changes = []

    for change in changes:

        field_name = change["field"]

        difference_percent = (
            change.get(
                "difference_percent"
            )
        )

        if field_name == "strategy_type":

            sensitive_changes.append(
                {
                    "field": field_name,
                    "severity": "HIGH",
                    "message": (
                        "Le type de stratégie "
                        "d'enchères sera remplacé."
                    ),
                }
            )

        elif (
            field_name == "target_cpa"
            and difference_percent
            is not None
            and abs(
                difference_percent
            ) >= 20
        ):

            sensitive_changes.append(
                {
                    "field": field_name,
                    "severity": "MEDIUM",
                    "message": (
                        "Le CPA cible changera de "
                        f"{difference_percent} %."
                    ),
                }
            )

        elif (
            field_name
            == "target_roas_percent"
            and difference_percent
            is not None
            and abs(
                difference_percent
            ) >= 20
        ):

            sensitive_changes.append(
                {
                    "field": field_name,
                    "severity": "MEDIUM",
                    "message": (
                        "Le ROAS cible changera de "
                        f"{difference_percent} %."
                    ),
                }
            )

        elif (
            change["change_type"]
            == "REMOVED"
        ):

            sensitive_changes.append(
                {
                    "field": field_name,
                    "severity": "MEDIUM",
                    "message": (
                        f"La valeur "
                        f"{change['label']} "
                        "sera supprimée."
                    ),
                }
            )

    # --------------------------------------------------------
    # RISQUE FINAL
    # --------------------------------------------------------

    analysis_risk_level = (
        analysis.get(
            "risk_level",
            "LOW",
        )
    )

    preview_risk_level = (
        analysis_risk_level
    )

    if any(
        item["severity"] == "HIGH"
        for item in sensitive_changes
    ):
        preview_risk_level = "HIGH"

    elif (
        sensitive_changes
        and preview_risk_level == "LOW"
    ):
        preview_risk_level = "MEDIUM"

    # --------------------------------------------------------
    # DETECTION D'UNE ABSENCE DE CHANGEMENT
    # --------------------------------------------------------

    no_change_detected = (
        len(changes) == 0
    )

    if no_change_detected:
        preview_status = "NO_CHANGE"

        next_action = "NO_ACTION_REQUIRED"

        confirmation_required = False

        message = (
            "La configuration proposée est "
            "identique à la configuration actuelle. "
            "Aucune modification n'est nécessaire."
        )

    else:
        preview_status = "READY_FOR_CONFIRMATION"

        next_action = (
            "REQUEST_CONFIRMATION_CODE"
        )

        confirmation_required = True

        message = (
            "La prévisualisation est prête. "
            "Aucune modification n'a été appliquée. "
            "Une confirmation explicite et le code "
            "de confirmation seront requis avant "
            "l'exécution."
        )

    # --------------------------------------------------------
    # IDENTIFIANT DE PREVISUALISATION
    # --------------------------------------------------------

    preview_payload = {
        "customer_id": analysis[
            "customer_id"
        ],

        "campaign_id": analysis[
            "campaign_id"
        ],

        "current_configuration": (
            current_configuration
        ),

        "proposed_configuration": (
            proposed_configuration
        ),

        "changes": changes,
    }

    preview_payload_json = json.dumps(
        preview_payload,
        sort_keys=True,
        default=str,
        ensure_ascii=True,
    )

    preview_id = hashlib.sha256(
        preview_payload_json.encode(
            "utf-8"
        )
    ).hexdigest()[:24]

    # --------------------------------------------------------
    # RESUME LISIBLE
    # --------------------------------------------------------

    readable_summary = (
        f"Campagne : "
        f"{analysis['campaign_name']}. "
        f"Stratégie actuelle : "
        f"{current_strategy_type}. "
        f"Stratégie proposée : "
        f"{proposed_strategy_type}. "
    )

    if no_change_detected:
        readable_summary += (
            "Aucun changement n'a été détecté."
        )

    else:
        readable_summary += (
            f"{len(changes)} changement"
            + (
                "s"
                if len(changes) > 1
                else ""
            )
            + " sera"
            + (
                "nt"
                if len(changes) > 1
                else ""
            )
            + " soumis à confirmation."
        )

    # --------------------------------------------------------
    # REPONSE
    # --------------------------------------------------------

    return {
        "customer_id": analysis[
            "customer_id"
        ],

        "campaign_id": analysis[
            "campaign_id"
        ],

        "campaign_name": analysis[
            "campaign_name"
        ],

        "campaign_status": analysis[
            "campaign_status"
        ],

        "channel_type": analysis[
            "channel_type"
        ],

        "period": analysis[
            "period"
        ],

        "preview_id": preview_id,

        "preview_status": (
            preview_status
        ),

        "compatible": True,

        "current_configuration": (
            current_configuration
        ),

        "proposed_configuration": (
            proposed_configuration
        ),

        "changes_count": len(
            changes
        ),

        "changes": changes,

        "sensitive_changes": (
            sensitive_changes
        ),

        "performance": analysis[
            "performance"
        ],

        "risk_level": (
            preview_risk_level
        ),

        "errors": analysis.get(
            "errors",
            [],
        ),

        "warnings": analysis.get(
            "warnings",
            [],
        ),

        "observations": analysis.get(
            "observations",
            [],
        ),

        "recommendations": analysis.get(
            "recommendations",
            [],
        ),

        "summary": readable_summary,

        "message": message,

        "modification_applied": False,

        "confirmation_required": (
            confirmation_required
        ),

        "next_action": next_action,
    }
# ============================================================
# verify_bidding_confirmation_code
# ============================================================
def verify_bidding_confirmation_code(
    provided_code: str,
):
    """
    Vérifie le code fourni par l'utilisateur contre
    CONFIRMATION_CODE stocké dans Google Cloud.

    La valeur attendue n'est jamais retournée,
    journalisée ou exposée par l'API.
    """

    expected_code = os.getenv(
        "CONFIRMATION_CODE"
    )

    if not expected_code:

        raise ValueError(
            "La variable CONFIRMATION_CODE "
            "n'est pas configurée dans Google Cloud."
        )

    provided_value = (
        provided_code or ""
    ).strip()

    expected_value = (
        expected_code or ""
    ).strip()

    if not hmac.compare_digest(
        provided_value,
        expected_value,
    ):
        raise PermissionError(
            "Code de confirmation invalide."
        )
# ============================================================
# UPDATE BIDDING STRATEGY
# ============================================================
def update_bidding_strategy(
    client: GoogleAdsClient,
    request: UpdateBiddingStrategyRequest,
):
    """
    Met à jour réellement la stratégie d'enchères
    d'une campagne Google Ads.

    Sécurité et workflow :

    1. Vérifie CONFIRMATION_CODE.
    2. Relance la prévisualisation.
    3. Vérifie le preview_id.
    4. Refuse toute demande incompatible.
    5. Applique la mutation Google Ads.
    6. Relit la campagne.
    7. Retourne la configuration vérifiée.

    Le code de confirmation n'est jamais retourné.
    """

    # --------------------------------------------------------
    # NORMALISATION
    # --------------------------------------------------------

    customer_id = (
        str(request.customer_id)
        .replace("-", "")
        .strip()
    )

    campaign_id = (
        str(request.campaign_id)
        .replace("-", "")
        .strip()
    )

    if not customer_id.isdigit():
        raise ValueError(
            "Le customer_id doit contenir "
            "uniquement des chiffres."
        )

    if not campaign_id.isdigit():
        raise ValueError(
            "Le campaign_id doit contenir "
            "uniquement des chiffres."
        )

    # --------------------------------------------------------
    # CONFIRMATION CODE
    # --------------------------------------------------------

    verify_bidding_confirmation_code(
        request.confirmation_code
    )

    # --------------------------------------------------------
    # NOUVELLE PRÉVISUALISATION
    # --------------------------------------------------------

    preview_request = (
        PreviewBiddingStrategyUpdateRequest(
            customer_id=customer_id,
            campaign_id=campaign_id,
            period=request.period,
            requested_strategy_type=(
                request.requested_strategy_type
            ),
            target_action=(
                request.target_action
            ),
            target_cpa=request.target_cpa,
            target_roas_percent=(
                request.target_roas_percent
            ),
            cpc_bid_ceiling=(
                request.cpc_bid_ceiling
            ),
            change_percent=(
                request.change_percent
            ),
            target_impression_share_percent=(
                request
                .target_impression_share_percent
            ),
            target_impression_location=(
                request
                .target_impression_location
            ),
            reason=request.reason,
        )
    )

    current_preview = (
        preview_bidding_strategy_update(
            client=client,
            request=preview_request,
        )
    )

    # --------------------------------------------------------
    # VALIDATION DE LA PRÉVISUALISATION
    # --------------------------------------------------------

    if not current_preview.get(
        "compatible",
        False,
    ):
        raise ValueError(
            "La modification n'est plus compatible "
            "avec la configuration actuelle."
        )

    if (
        current_preview.get(
            "preview_status"
        )
        != "READY_FOR_CONFIRMATION"
    ):
        raise ValueError(
            "La prévisualisation n'est pas prête "
            "pour l'exécution."
        )

    if (
        current_preview.get(
            "preview_id"
        )
        != request.preview_id
    ):
        raise ValueError(
            "La configuration de la campagne a changé "
            "ou la demande ne correspond plus à la "
            "prévisualisation confirmée. Relancez la "
            "prévisualisation avant de continuer."
        )

    if (
        current_preview.get(
            "changes_count",
            0,
        )
        <= 0
    ):
        raise ValueError(
            "Aucune modification n'est nécessaire."
        )

    # --------------------------------------------------------
    # CONFIGURATIONS AVANT / APRÈS
    # --------------------------------------------------------

    previous_configuration = (
        current_preview[
            "current_configuration"
        ]
    )

    proposed_configuration = (
        current_preview[
            "proposed_configuration"
        ]
    )

    strategy_type = (
        proposed_configuration[
            "strategy_type"
        ]
    )

    target_action = (
        proposed_configuration[
            "target_action"
        ]
    )

    target_cpa = (
        proposed_configuration.get(
            "target_cpa"
        )
    )

    target_roas_percent = (
        proposed_configuration.get(
            "target_roas_percent"
        )
    )

    cpc_bid_ceiling = (
        proposed_configuration.get(
            "cpc_bid_ceiling"
        )
    )

    impression_share_percent = (
        proposed_configuration.get(
            "target_impression_share_percent"
        )
    )

    impression_location = (
        proposed_configuration.get(
            "target_impression_location"
        )
    )

    # --------------------------------------------------------
    # OBJETS GOOGLE ADS
    # --------------------------------------------------------

    campaign_service = client.get_service(
        "CampaignService"
    )

    campaign_operation = client.get_type(
        "CampaignOperation"
    )

    campaign = (
        campaign_operation.update
    )

    campaign.resource_name = (
        campaign_service.campaign_path(
            customer_id,
            campaign_id,
        )
    )

    update_paths = []

    # --------------------------------------------------------
    # MAXIMISER LES CONVERSIONS / tCPA
    # --------------------------------------------------------

    if (
        strategy_type
        == "MAXIMIZE_CONVERSIONS"
    ):
        maximize_conversions = (
            client.get_type(
                "MaximizeConversions"
            )
        )

        if target_cpa is not None:

            maximize_conversions.target_cpa_micros = int(
                round(
                    float(target_cpa)
                    * 1_000_000
                )
            )

        campaign.maximize_conversions = (
            maximize_conversions
        )

        update_paths.append(
            "maximize_conversions"
        )

        update_paths.append(
            "maximize_conversions."
            "target_cpa_micros"
        )

    # --------------------------------------------------------
    # MAXIMISER LA VALEUR / tROAS
    # --------------------------------------------------------

    elif (
        strategy_type
        == "MAXIMIZE_CONVERSION_VALUE"
    ):
        maximize_conversion_value = (
            client.get_type(
                "MaximizeConversionValue"
            )
        )

        if target_roas_percent is not None:

            maximize_conversion_value.target_roas = (
                round(
                    float(
                        target_roas_percent
                    )
                    / 100,
                    6,
                )
            )

        campaign.maximize_conversion_value = (
            maximize_conversion_value
        )

        update_paths.append(
            "maximize_conversion_value"
        )

        update_paths.append(
            "maximize_conversion_value.target_roas"
        )

    # --------------------------------------------------------
    # MAXIMISER LES CLICS
    # Google Ads expose cette stratégie via TARGET_SPEND.
    # --------------------------------------------------------

    elif strategy_type == "MAXIMIZE_CLICKS":

        target_spend = client.get_type(
            "TargetSpend"
        )

        if cpc_bid_ceiling is not None:

            target_spend.cpc_bid_ceiling_micros = int(
                round(
                    float(cpc_bid_ceiling)
                    * 1_000_000
                )
            )

        campaign.target_spend = (
            target_spend
        )

        update_paths.append(
            "target_spend"
        )

        update_paths.append(
            "target_spend."
            "cpc_bid_ceiling_micros"
        )

    # --------------------------------------------------------
    # CPC MANUEL
    # --------------------------------------------------------

    elif strategy_type == "MANUAL_CPC":

        manual_cpc = client.get_type(
            "ManualCpc"
        )

        manual_cpc.enhanced_cpc_enabled = False

        campaign.manual_cpc = (
            manual_cpc
        )

        update_paths.append(
            "manual_cpc"
        )

        update_paths.append(
            "manual_cpc."
            "enhanced_cpc_enabled"
        )

    # --------------------------------------------------------
    # TAUX D'IMPRESSIONS CIBLE
    # --------------------------------------------------------

    elif (
        strategy_type
        == "TARGET_IMPRESSION_SHARE"
    ):
        if impression_share_percent is None:
            raise ValueError(
                "La part d'impressions cible "
                "est obligatoire."
            )

        if impression_location is None:
            raise ValueError(
                "L'emplacement cible est obligatoire."
            )

        if cpc_bid_ceiling is None:
            raise ValueError(
                "La limite CPC maximale est "
                "obligatoire."
            )

        target_impression_share = (
            client.get_type(
                "TargetImpressionShare"
            )
        )

        target_impression_share.location_fraction_micros = int(
            round(
                (
                    float(
                        impression_share_percent
                    )
                    / 100
                )
                * 1_000_000
            )
        )

        target_impression_share.cpc_bid_ceiling_micros = int(
            round(
                float(cpc_bid_ceiling)
                * 1_000_000
            )
        )

        if (
            impression_location
            == "ANYWHERE_ON_PAGE"
        ):
            target_impression_share.location = (
                client.enums
                .TargetImpressionShareLocationEnum
                .ANYWHERE_ON_PAGE
            )

        elif (
            impression_location
            == "TOP_OF_PAGE"
        ):
            target_impression_share.location = (
                client.enums
                .TargetImpressionShareLocationEnum
                .TOP_OF_PAGE
            )

        elif (
            impression_location
            == "ABSOLUTE_TOP_OF_PAGE"
        ):
            target_impression_share.location = (
                client.enums
                .TargetImpressionShareLocationEnum
                .ABSOLUTE_TOP_OF_PAGE
            )

        else:
            raise ValueError(
                "Emplacement Taux d'impressions "
                "cible non reconnu."
            )

        campaign.target_impression_share = (
            target_impression_share
        )

        update_paths.append(
            "target_impression_share"
        )

        update_paths.append(
            "target_impression_share."
            "location"
        )

        update_paths.append(
            "target_impression_share."
            "location_fraction_micros"
        )

        update_paths.append(
            "target_impression_share."
            "cpc_bid_ceiling_micros"
        )

    else:
        raise ValueError(
            "La stratégie demandée n'est pas "
            "prise en charge par la mutation."
        )

    # --------------------------------------------------------
    # UPDATE MASK
    # --------------------------------------------------------

    campaign_operation.update_mask.paths.extend(
        list(
            dict.fromkeys(
                update_paths
            )
        )
    )

    # --------------------------------------------------------
    # MUTATION GOOGLE ADS
    # --------------------------------------------------------

    response = (
        campaign_service.mutate_campaigns(
            customer_id=customer_id,
            operations=[
                campaign_operation
            ],
        )
    )

    if not response.results:
        raise ValueError(
            "Google Ads n'a retourné aucune "
            "ressource modifiée."
        )

    resource_name = (
        response.results[0]
        .resource_name
    )

    # --------------------------------------------------------
    # RELECTURE APRÈS MUTATION
    # --------------------------------------------------------

    verified_configuration = (
        get_bidding_strategy_details(
            client=client,
            customer_id=customer_id,
            campaign_id=campaign_id,
        )
    )

    # --------------------------------------------------------
    # VÉRIFICATION DE LA STRATÉGIE ENREGISTRÉE
    # --------------------------------------------------------

    verified_strategy_type = (
        verified_configuration[
            "strategy_type"
        ]
    )

    expected_google_strategy_type = (
        strategy_type
    )

    # La stratégie Maximiser les clics peut être
    # retournée par Google Ads sous TARGET_SPEND.
    if strategy_type == "MAXIMIZE_CLICKS":

        expected_google_strategy_type = (
            "TARGET_SPEND"
        )

    strategy_verified = (
        verified_strategy_type
        == expected_google_strategy_type
    )

    verification_warnings = []

    if not strategy_verified:

        verification_warnings.append(
            {
                "code": (
                    "STRATEGY_VERIFICATION_MISMATCH"
                ),
                "message": (
                    "La stratégie retournée après "
                    "mutation ne correspond pas "
                    "exactement à la stratégie attendue."
                ),
                "expected": (
                    expected_google_strategy_type
                ),
                "actual": (
                    verified_strategy_type
                ),
            }
        )

    # --------------------------------------------------------
    # RÉPONSE
    # --------------------------------------------------------

    return {
        "status": "UPDATED",

        "confirmation_verified": True,

        "customer_id": customer_id,

        "campaign_id": campaign_id,

        "campaign_name": (
            current_preview[
                "campaign_name"
            ]
        ),

        "resource_name": (
            resource_name
        ),

        "preview_id": (
            current_preview[
                "preview_id"
            ]
        ),

        "previous_configuration": (
            previous_configuration
        ),

        "requested_configuration": (
            proposed_configuration
        ),

        "verified_configuration": (
            verified_configuration
        ),

        "strategy_verified": (
            strategy_verified
        ),

        "verification_warnings": (
            verification_warnings
        ),

        "changes": (
            current_preview[
                "changes"
            ]
        ),

        "risk_level": (
            current_preview[
                "risk_level"
            ]
        ),

        "message": (
            "La stratégie d'enchères a été "
            "modifiée dans Google Ads puis relue "
            "pour vérification."
        ),

        "modification_applied": True,

        "confirmation_required": False,

        "next_action": (
            "MONITOR_PERFORMANCE"
        ),
    }
