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
