import os
import secrets

from fastapi import APIRouter
from google.ads.googleads.client import GoogleAdsClient
from google.api_core import protobuf_helpers
from main import get_google_ads_client

router = APIRouter(
  tags=["Ad Mutations"]
)

#---------------------------------------------------------------------
# PAUSE AD
#---------------------------------------------------------------------

@router.post("/pause-ad")
def pause_ad(
    customer_id: str,
    ad_id: str,
    confirmation_code: str,
):
    try:

        expected_code = os.getenv(
            "CONFIRMATION_CODE"
        )

        if not secrets.compare_digest(
            str(confirmation_code),
            str(expected_code),
        ):
            return {
                "status": "CONFIRMATION_REQUIRED",
                "error": "Code de confirmation incorrect."
            }

        client = get_google_ads_client()

        service = client.get_service(
            "AdGroupAdService"
        )

        operation = client.get_type(
            "AdGroupAdOperation"
        )

        ad_group_ad = operation.update

        ad_group_ad.resource_name = (
            ad_id
        )

        ad_group_ad.status = (
            client.enums
            .AdGroupAdStatusEnum
            .PAUSED
        )

        client.copy_from(
            operation.update_mask,
            protobuf_helpers.field_mask(
                None,
                ad_group_ad._pb,
            ),
        )

        response = (
            service.mutate_ad_group_ads(
                customer_id=customer_id,
                operations=[operation],
            )
        )

        return {
            "status": "SUCCESS",
            "ad_status": "PAUSED",
            "resource_name":
                response.results[
                    0
                ].resource_name,
        }

    except Exception as error:

        return {
            "status": "FAILED",
            "error": str(error),
        }

#---------------------------------------------------------------------
# enable AD
#---------------------------------------------------------------------
@router.post("/enable-ad")
def enable_ad(
    customer_id: str,
    ad_id: str,
    confirmation_code: str,
):
    try:

        expected_code = os.getenv(
            "CONFIRMATION_CODE"
        )

        if not secrets.compare_digest(
            str(confirmation_code),
            str(expected_code),
        ):
            return {
                "status": "CONFIRMATION_REQUIRED",
                "error": "Code de confirmation incorrect."
            }

        client = get_google_ads_client()

        service = client.get_service(
            "AdGroupAdService"
        )

        operation = client.get_type(
            "AdGroupAdOperation"
        )

        ad_group_ad = operation.update

        ad_group_ad.resource_name = (
            ad_id
        )

        ad_group_ad.status = (
            client.enums
            .AdGroupAdStatusEnum
            .ENABLED
        )

        client.copy_from(
            operation.update_mask,
            protobuf_helpers.field_mask(
                None,
                ad_group_ad._pb,
            ),
        )

        response = (
            service.mutate_ad_group_ads(
                customer_id=customer_id,
                operations=[operation],
            )
        )

        return {
            "status": "SUCCESS",
            "ad_status": "ENABLED",
            "resource_name":
                response.results[
                    0
                ].resource_name,
        }

    except Exception as error:

        return {
            "status": "FAILED",
            "error": str(error),
        }
#---------------------------------------------------------------------
# enable AD
#---------------------------------------------------------------------
@router.post("/remove-ad")
def remove_ad(
    customer_id: str,
    ad_id: str,
    confirmation_code: str,
):
    try:

        expected_code = os.getenv(
            "CONFIRMATION_CODE"
        )

        if not secrets.compare_digest(
            str(confirmation_code),
            str(expected_code),
        ):
            return {
                "status": "CONFIRMATION_REQUIRED",
                "error": "Code de confirmation incorrect."
            }

        client = get_google_ads_client()

        service = client.get_service(
            "AdGroupAdService"
        )

        operation = client.get_type(
            "AdGroupAdOperation"
        )

        operation.remove = ad_id

        response = (
            service.mutate_ad_group_ads(
                customer_id=customer_id,
                operations=[operation],
            )
        )

        return {
            "status": "SUCCESS",
            "removed": True,
            "resource_name":
                response.results[
                    0
                ].resource_name,
        }

    except Exception as error:

        return {
            "status": "FAILED",
            "error": str(error),
        }
