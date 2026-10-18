from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class BiddingStrategyType(str, Enum):
    MAXIMIZE_CONVERSIONS = (
        "MAXIMIZE_CONVERSIONS"
    )

    MAXIMIZE_CONVERSION_VALUE = (
        "MAXIMIZE_CONVERSION_VALUE"
    )

    MAXIMIZE_CLICKS = (
        "MAXIMIZE_CLICKS"
    )

    MANUAL_CPC = (
        "MANUAL_CPC"
    )

    TARGET_IMPRESSION_SHARE = (
        "TARGET_IMPRESSION_SHARE"
    )

class PreviewBiddingStrategyUpdateRequest(
    AnalyzeStrategyChangeRequest
):
    """
    Requête de prévisualisation d'une modification
    de stratégie d'enchères.
    """
    pass

class BiddingStrategyDetailsRequest(BaseModel):
    customer_id: str
    campaign_id: str


class BiddingStrategiesRequest(BaseModel):
    customer_id: str
    strategy_type: Optional[str] = None
    
class BiddingTargetAction(str, Enum):
    KEEP = "KEEP"
    SET = "SET"
    REMOVE = "REMOVE"
    INCREASE_PERCENT = "INCREASE_PERCENT"
    DECREASE_PERCENT = "DECREASE_PERCENT"


class TargetImpressionLocation(str, Enum):
    ANYWHERE_ON_PAGE = (
        "ANYWHERE_ON_PAGE"
    )

    TOP_OF_PAGE = (
        "TOP_OF_PAGE"
    )

    ABSOLUTE_TOP_OF_PAGE = (
        "ABSOLUTE_TOP_OF_PAGE"
    )


class AnalyzeStrategyChangeRequest(BaseModel):
    customer_id: str = Field(
        ...,
        description="ID du compte Google Ads.",
    )

    campaign_id: str = Field(
        ...,
        description="ID de la campagne Google Ads.",
    )

    period: str = Field(
        default="LAST_30_DAYS",
        description=(
            "Période Google Ads utilisée pour "
            "l'analyse des performances."
        ),
    )

    requested_strategy_type: (
        BiddingStrategyType
    ) = Field(
        ...,
        description=(
            "Nouvelle stratégie d'enchères "
            "demandée."
        ),
    )

    target_action: BiddingTargetAction = Field(
        default=BiddingTargetAction.KEEP,
        description=(
            "Action à appliquer sur la cible : "
            "KEEP, SET, REMOVE, "
            "INCREASE_PERCENT ou "
            "DECREASE_PERCENT."
        ),
    )

    target_cpa: Optional[float] = Field(
        default=None,
        gt=0,
        description=(
            "CPA cible demandé dans la devise "
            "du compte."
        ),
    )

    target_roas_percent: Optional[float] = Field(
        default=None,
        gt=0,
        description=(
            "ROAS cible en pourcentage. "
            "Exemple : 500 représente 500 %."
        ),
    )

    cpc_bid_ceiling: Optional[float] = Field(
        default=None,
        gt=0,
        description=(
            "Limite CPC maximale dans la devise "
            "du compte."
        ),
    )

    change_percent: Optional[float] = Field(
        default=None,
        gt=0,
        le=100,
        description=(
            "Pourcentage d'augmentation ou de "
            "réduction de la cible actuelle."
        ),
    )

    target_impression_share_percent: (
        Optional[float]
    ) = Field(
        default=None,
        gt=0,
        le=100,
        description=(
            "Part d'impressions cible en "
            "pourcentage."
        ),
    )

    target_impression_location: (
        Optional[TargetImpressionLocation]
    ) = Field(
        default=None,
        description=(
            "Emplacement visé pour la stratégie "
            "Taux d'impressions cible."
        ),
    )

    reason: Optional[str] = Field(
        default=None,
        description=(
            "Contexte ou raison de la demande."
        ),
    )


