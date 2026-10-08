#------------------------------------------------------------------------
# PAUSEE KEYWORD
#------------------------------------------------------------------------
@app.post("/pause-keyword")
def pause_keyword(
    customer_id: str,
    criterion_id: str,
    confirmation_code: str,
):
    try:

        expected_code = os.getenv(
            "CONFIRMATION_CODE"
        )

        if confirmation_code != expected_code:

            return {
                "status":
                    "CONFIRMATION_REQUIRED",

                "error":
                    "Code de confirmation incorrect."
            }

        client = get_google_ads_client()

        service = client.get_service(
            "AdGroupCriterionService"
        )

        operation = client.get_type(
            "AdGroupCriterionOperation"
        )

        criterion = operation.update

        criterion.resource_name = (
            f"customers/{customer_id}"
            f"/adGroupCriteria/{criterion_id}"
        )

        criterion.status = (
            client.enums
            .AdGroupCriterionStatusEnum
            .PAUSED
        )

        client.copy_from(
            operation.update_mask,
            protobuf_helpers.field_mask(
                None,
                criterion._pb,
            ),
        )

        response = (
            service
            .mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=[
                    operation
                ],
            )
        )

        return {
            "status":
                "SUCCESS",

            "resource_name":
                response.results[
                    0
                ].resource_name,

            "keyword_status":
                "PAUSED",
        }

    except Exception as error:

        return {
            "status":
                "FAILED",

            "error":
                str(error),
        }
#------------------------------------------------------------------------
# ENAVLE KEYWORD
#------------------------------------------------------------------------
@app.post("/enable-keyword")
def enable_keyword(
    customer_id: str,
    criterion_id: str,
    confirmation_code: str,
):
    try:

        expected_code = os.getenv(
            "CONFIRMATION_CODE"
        )

        if confirmation_code != expected_code:

            return {
                "status":
                    "CONFIRMATION_REQUIRED"
            }

        client = get_google_ads_client()

        service = client.get_service(
            "AdGroupCriterionService"
        )

        operation = client.get_type(
            "AdGroupCriterionOperation"
        )

        criterion = operation.update

        criterion.resource_name = (
            f"customers/{customer_id}"
            f"/adGroupCriteria/{criterion_id}"
        )

        criterion.status = (
            client.enums
            .AdGroupCriterionStatusEnum
            .ENABLED
        )

        client.copy_from(
            operation.update_mask,
            protobuf_helpers.field_mask(
                None,
                criterion._pb,
            ),
        )

        response = (
            service
            .mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=[
                    operation
                ],
            )
        )

        return {
            "status":
                "SUCCESS",

            "resource_name":
                response.results[
                    0
                ].resource_name,

            "keyword_status":
                "ENABLED",
        }

    except Exception as error:

        return {
            "status":
                "FAILED",
            "error":
                str(error),
        }
#------------------------------------------------------------------------
# REMOVE KEYWORD
#------------------------------------------------------------------------
@app.post("/remove-keyword")
def remove_keyword(
    customer_id: str,
    criterion_id: str,
    confirmation_code: str,
):
    try:

        expected_code = os.getenv(
            "CONFIRMATION_CODE"
        )

        if confirmation_code != expected_code:

            return {
                "status":
                    "CONFIRMATION_REQUIRED"
            }

        client = get_google_ads_client()

        service = client.get_service(
            "AdGroupCriterionService"
        )

        operation = client.get_type(
            "AdGroupCriterionOperation"
        )

        operation.remove = (
            f"customers/{customer_id}"
            f"/adGroupCriteria/{criterion_id}"
        )

        response = (
            service
            .mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=[
                    operation
                ],
            )
        )

        return {
            "status":
                "SUCCESS",

            "removed":
                True,

            "resource_name":
                response.results[
                    0
                ].resource_name,
        }

    except Exception as error:

        return {
            "status":
                "FAILED",

            "error":
                str(error),
        }
