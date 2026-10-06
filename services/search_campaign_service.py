from datetime import date, datetime
from typing import Any, Optional

from openpyxl import load_workbook


class SearchCampaignService:

    REQUIRED_SHEETS = {
        "Account & Campaign",
        "Ad Groups",
        "Ads",
    }

    @staticmethod
    def health():

        return {
            "status": "SUCCESS",
            "module": "SEARCH",
        }

    @staticmethod
    def _clean_text(
        value: Any,
    ) -> Optional[str]:

        if value is None:
            return None

        cleaned_value = str(
            value
        ).strip()

        return (
            cleaned_value
            if cleaned_value
            else None
        )

    @staticmethod
    def _format_date(
        value: Any,
    ) -> Optional[str]:

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

        cleaned_value = str(
            value
        ).strip()

        return (
            cleaned_value
            if cleaned_value
            else None
        )

    @staticmethod
    def _split_locations(
        value: Any,
    ) -> list[str]:

        if value is None:
            return []

        return [
            location.strip()
            for location in str(
                value
            ).split(";")
            if location.strip()
        ]

    @staticmethod
    def _remove_duplicates(
        values: list[str],
    ) -> list[str]:

        unique_values = []
        seen_values = set()

        for value in values:

            normalized_value = (
                value
                .strip()
                .casefold()
            )

            if (
                not normalized_value
                or normalized_value
                in seen_values
            ):
                continue

            seen_values.add(
                normalized_value
            )

            unique_values.append(
                value.strip()
            )

        return unique_values

    @staticmethod
    def _read_campaign(
        workbook,
    ) -> dict:

        account_sheet = workbook[
            "Account & Campaign"
        ]

        return {
            "account_name":
                SearchCampaignService
                ._clean_text(
                    account_sheet[
                        "C4"
                    ].value
                ),

            "customer_id":
                SearchCampaignService
                ._clean_text(
                    account_sheet[
                        "C5"
                    ].value
                ),

            "campaign_name":
                SearchCampaignService
                ._clean_text(
                    account_sheet[
                        "C6"
                    ].value
                ),

            "objective":
                SearchCampaignService
                ._clean_text(
                    account_sheet[
                        "C7"
                    ].value
                ),

            "daily_budget":
                account_sheet[
                    "C8"
                ].value,

            "currency":
                SearchCampaignService
                ._clean_text(
                    account_sheet[
                        "C9"
                    ].value
                ),

            "language":
                SearchCampaignService
                ._clean_text(
                    account_sheet[
                        "C10"
                    ].value
                ),

            "locations":
                SearchCampaignService
                ._split_locations(
                    account_sheet[
                        "C11"
                    ].value
                ),

            "network":
                SearchCampaignService
                ._clean_text(
                    account_sheet[
                        "C12"
                    ].value
                ),

            "bidding_strategy":
                SearchCampaignService
                ._clean_text(
                    account_sheet[
                        "C13"
                    ].value
                ),

            "start_date":
                SearchCampaignService
                ._format_date(
                    account_sheet[
                        "C14"
                    ].value
                ),

            "end_date":
                SearchCampaignService
                ._format_date(
                    account_sheet[
                        "C15"
                    ].value
                ),

            "status":
                SearchCampaignService
                ._clean_text(
                    account_sheet[
                        "C16"
                    ].value
                ),

            "label":
                SearchCampaignService
                ._clean_text(
                    account_sheet[
                        "C17"
                    ].value
                ),
        }

    @staticmethod
    def _read_ad_groups(
        workbook,
        campaign_name: Optional[str],
    ) -> list[dict]:

        ad_groups_sheet = workbook[
            "Ad Groups"
        ]

        ad_groups = []

        for row_number in range(
            4,
            ad_groups_sheet.max_row + 1,
        ):

            row_campaign_name = (
                SearchCampaignService
                ._clean_text(
                    ad_groups_sheet.cell(
                        row=row_number,
                        column=1,
                    ).value
                )
            )

            ad_group_name = (
                SearchCampaignService
                ._clean_text(
                    ad_groups_sheet.cell(
                        row=row_number,
                        column=2,
                    ).value
                )
            )

            final_url = (
                SearchCampaignService
                ._clean_text(
                    ad_groups_sheet.cell(
                        row=row_number,
                        column=3,
                    ).value
                )
            )

            if not ad_group_name:
                continue

            if (
                campaign_name
                and row_campaign_name
                and row_campaign_name
                != campaign_name
            ):
                continue

            ad_group = {
                "campaign_name":
                    row_campaign_name,

                "name":
                    ad_group_name,

                "final_url":
                    final_url,

                "path1":
                    SearchCampaignService
                    ._clean_text(
                        ad_groups_sheet.cell(
                            row=row_number,
                            column=4,
                        ).value
                    ),

                "path2":
                    SearchCampaignService
                    ._clean_text(
                        ad_groups_sheet.cell(
                            row=row_number,
                            column=6,
                        ).value
                    ),

                "utm_source":
                    SearchCampaignService
                    ._clean_text(
                        ad_groups_sheet.cell(
                            row=row_number,
                            column=8,
                        ).value
                    ),

                "utm_medium":
                    SearchCampaignService
                    ._clean_text(
                        ad_groups_sheet.cell(
                            row=row_number,
                            column=9,
                        ).value
                    ),

                "utm_campaign":
                    SearchCampaignService
                    ._clean_text(
                        ad_groups_sheet.cell(
                            row=row_number,
                            column=10,
                        ).value
                    ),

                "utm_term":
                    SearchCampaignService
                    ._clean_text(
                        ad_groups_sheet.cell(
                            row=row_number,
                            column=11,
                        ).value
                    ),

                "utm_content":
                    SearchCampaignService
                    ._clean_text(
                        ad_groups_sheet.cell(
                            row=row_number,
                            column=12,
                        ).value
                    ),

                "tracking_url":
                    SearchCampaignService
                    ._clean_text(
                        ad_groups_sheet.cell(
                            row=row_number,
                            column=13,
                        ).value
                    ),

                "source_row":
                    row_number,
            }

            ad_groups.append(
                ad_group
            )

        return ad_groups

    @staticmethod
    def _read_ads(
        workbook,
        campaign_name: Optional[str],
    ) -> list[dict]:

        ads_sheet = workbook[
            "Ads"
        ]

        ads_by_group = {}

        for row_number in range(
            4,
            ads_sheet.max_row + 1,
        ):

            row_campaign_name = (
                SearchCampaignService
                ._clean_text(
                    ads_sheet.cell(
                        row=row_number,
                        column=1,
                    ).value
                )
            )

            ad_group_name = (
                SearchCampaignService
                ._clean_text(
                    ads_sheet.cell(
                        row=row_number,
                        column=2,
                    ).value
                )
            )

            headline = (
                SearchCampaignService
                ._clean_text(
                    ads_sheet.cell(
                        row=row_number,
                        column=3,
                    ).value
                )
            )

            description = (
                SearchCampaignService
                ._clean_text(
                    ads_sheet.cell(
                        row=row_number,
                        column=5,
                    ).value
                )
            )

            if not ad_group_name:
                continue

            if (
                campaign_name
                and row_campaign_name
                and row_campaign_name
                != campaign_name
            ):
                continue

            group_key = (
                row_campaign_name
                or campaign_name,
                ad_group_name,
            )

            if group_key not in ads_by_group:

                ads_by_group[
                    group_key
                ] = {
                    "campaign_name":
                        row_campaign_name
                        or campaign_name,

                    "ad_group_name":
                        ad_group_name,

                    "ad_type":
                        "RESPONSIVE_SEARCH_AD",

                    "headlines":
                        [],

                    "descriptions":
                        [],

                    "path1":
                        None,

                    "path2":
                        None,

                    "final_url":
                        None,

                    "label":
                        None,

                    "source_rows":
                        [],
                }

            ad = ads_by_group[
                group_key
            ]

            if headline:
                ad["headlines"].append(
                    headline
                )

            if description:
                ad[
                    "descriptions"
                ].append(
                    description
                )

            path1 = (
                SearchCampaignService
                ._clean_text(
                    ads_sheet.cell(
                        row=row_number,
                        column=7,
                    ).value
                )
            )

            path2 = (
                SearchCampaignService
                ._clean_text(
                    ads_sheet.cell(
                        row=row_number,
                        column=9,
                    ).value
                )
            )

            final_url = (
                SearchCampaignService
                ._clean_text(
                    ads_sheet.cell(
                        row=row_number,
                        column=11,
                    ).value
                )
            )

            label = (
                SearchCampaignService
                ._clean_text(
                    ads_sheet.cell(
                        row=row_number,
                        column=12,
                    ).value
                )
            )

            if path1:
                ad["path1"] = path1

            if path2:
                ad["path2"] = path2

            if final_url:
                ad[
                    "final_url"
                ] = final_url

            if label:
                ad["label"] = label

            ad["source_rows"].append(
                row_number
            )

        ads = []

        for ad in ads_by_group.values():

            ad["headlines"] = (
                SearchCampaignService
                ._remove_duplicates(
                    ad["headlines"]
                )
            )

            ad["descriptions"] = (
                SearchCampaignService
                ._remove_duplicates(
                    ad["descriptions"]
                )
            )

            ad[
                "headlines_count"
            ] = len(
                ad["headlines"]
            )

            ad[
                "descriptions_count"
            ] = len(
                ad["descriptions"]
            )

            ads.append(
                ad
            )

        return ads

    @staticmethod
    def _validate_campaign(
        campaign: dict,
    ) -> list[dict]:

        errors = []

        required_fields = [
            "account_name",
            "customer_id",
            "campaign_name",
            "objective",
            "daily_budget",
            "currency",
            "language",
            "locations",
            "network",
            "bidding_strategy",
            "status",
        ]

        for field_name in required_fields:

            value = campaign.get(
                field_name
            )

            if value in {
                None,
                "",
            } or value == []:

                errors.append(
                    {
                        "section":
                            "CAMPAIGN",

                        "field":
                            field_name,

                        "error":
                            "REQUIRED_FIELD_MISSING",
                    }
                )

        daily_budget = campaign.get(
            "daily_budget"
        )

        if (
            daily_budget is not None
            and (
                not isinstance(
                    daily_budget,
                    (
                        int,
                        float,
                    ),
                )
                or daily_budget <= 0
            )
        ):
            errors.append(
                {
                    "section":
                        "CAMPAIGN",

                    "field":
                        "daily_budget",

                    "error":
                        "DAILY_BUDGET_MUST_BE_POSITIVE",
                }
            )

        return errors

    @staticmethod
    def _validate_ad_groups(
        ad_groups: list[dict],
    ) -> list[dict]:

        errors = []

        if not ad_groups:

            errors.append(
                {
                    "section":
                        "AD_GROUPS",

                    "error":
                        "AT_LEAST_ONE_AD_GROUP_REQUIRED",
                }
            )

            return errors

        seen_names = set()

        for ad_group in ad_groups:

            name = ad_group.get(
                "name"
            )

            normalized_name = (
                name.casefold               errors.append(
                    {
                        "section":
                            "AD_GROUPS",

                        "source_row":
                            ad_group.get(
                                "source_row"
                            ),

                        "field":
                            "name",

                        "error":
                            "AD_GROUP_NAME_REQUIRED",
                    }
                )

            elif normalized_name in seen_names:

                errors.append(
                    {
                        "section":
                            "AD_GROUPS",

                        "source_row":
                            ad_group.get(
                                "source_row"
                            ),

                        "field":
                            "name",

                        "error":
                            "DUPLICATE_AD_GROUP_NAME",
                    }
                )

            else:
                seen_names.add(
                    normalized_name
                )

            if not ad_group.get(
                "final_url"
            ):

                errors.append(
                    {
                        "section":
                            "AD_GROUPS",

                        "ad_group":
                            name,

                        "field":
                            "final_url",

                        "error":
                            "FINAL_URL_REQUIRED",
                    }
                )

            path1 = (
                ad_group.get(
                    "path1"
                )
                or ""
            )

            path2 = (
                ad_group.get(
                    "path2"
                )
                or ""
            )

            if len(path1) > 15:

                errors.append(
                    {
                        "section":
                            "AD_GROUPS",

                        "ad_group":
                            name,

                        "field":
                            "path1",

                        "error":
                            "PATH_TOO_LONG",

                        "maximum":
                            15,

                        "actual":
                            len(path1),
                    }
                )

            if len(path2) > 15:

                errors.append(
                    {
                        "section":
                            "AD_GROUPS",

                        "ad_group":
                            name,

                        "field":
                            "path2",

                        "error":
                            "PATH_TOO_LONG",

                        "maximum":
                            15,

                        "actual":
                            len(path2),
                    }
                )

            if path2 and not path1:

                errors.append(
                    {
                        "section":
                            "AD_GROUPS",

                        "ad_group":
                            name,

                        "field":
                            "path2",

                        "error":
                            "PATH2_REQUIRES_PATH1",
                    }
                )

        return errors

    @staticmethod
    def _validate_ads(
        ads: list[dict],
    ) -> listerrors = []

        if not ads:

            errors.append(
                {
                    "section":
                        "ADS",

                    "error":
                        "AT_LEAST_ONE_RSA_REQUIRED",
                }
            )

            return errors

        for ad in ads:

            ad_group_name = (
                ad.get(
                    "ad_group_name"
                )
            )

            headlines = ad.get(
                "headlines",
                [],
            )

            descriptions = ad.get(
                "descriptions",
                [],
            )

            if len(headlines) < 3:

                errors.append(
                    {
                        "section":
                            "ADS",

                        "ad_group":
                            ad_group_name,

                        "field":
                            "headlines",

                        "error":
                            "MINIMUM_THREE_HEADLINES",

                        "actual":
                            len(headlines),
                    }
                )

            if len(headlines) > 15:

                errors.append(
                    {
                        "section":
                            "ADS",

                        "ad_group":
                            ad_group_name,

                        "field":
                            "headlines",

                        "error":
                            "MAXIMUM_FIFTEEN_HEADLINES",

                        "actual":
                            len(headlines),
                    }
                )

            if len(descriptions) < 2:

                errors.append(
                    {
                        "section":
                            "ADS",

                        "ad_group":
                            ad_group_name,

                        "field":
                            "descriptions",

                        "error":
                            "MINIMUM_TWO_DESCRIPTIONS",

                        "actual":
                            len(descriptions),
                    }
                )

            if len(descriptions) > 4:

                errors.append(
                    {
                        "section":
                            "ADS",

                        "ad_group":
                            ad_group_name,

                        "field":
                            "descriptions",

                        "error":
                            "MAXIMUM_FOUR_DESCRIPTIONS",

                        "actual":
                            len(descriptions),
                    }
                )

            for position, headline in enumerate(
                headlines,
                start=1,
            ):

                if len(headline) > 30:

                    errors.append(
                        {
                            "section":
                                "ADS",

                            "ad_group":
                                ad_group_name,

                            "field":
                                f"headline_{position}",

                            "error":
                                "HEADLINE_TOO_LONG",

                            "maximum":
                                30,

                            "actual":
                                len(headline),

                            "value":
                                headline,
                        }
                    )

                if "!" in headline:

                    errors.append(
                        {
                            "section":
                                "ADS",

                            "ad_group":
                                ad_group_name,

                            "field":
                                f"headline_{position}",

                            "error":
                                "EXCLAMATION_NOT_ALLOWED_IN_HEADLINE",

                            "value":
                                headline,
                        }
                    )

            total_exclamation_marks = 0

            for position, description in enumerate(
                descriptions,
                start=1,
            ):

                if len(description) > 90:

                    errors.append(
                        {
                            "section":
                                "ADS",

                            "ad_group":
                                ad_group_name,

                            "field":
                                f"description_{position}",

                            "error":
                                "DESCRIPTION_TOO_LONG",

                            "maximum":
                                90,

                            "actual":
                                len(
                                    description
                                ),

                            "value":
                                description,
                        }
                    )

                total_exclamation_marks += (
                    description.count(
                        "!"
                    )
                )

            if total_exclamation_marks > 1:

                errors.append(
                    {
                        "section":
                            "ADS",

                        "ad_group":
                            ad_group_name,

                        "field":
                            "descriptions",

                        "error":
                            "TOO_MANY_EXCLAMATION_MARKS",

                        "maximum":
                            1,

                        "actual":
                            total_exclamation_marks,
                    }
                )

            if not ad.get(
                "final_url"
            ):

                errors.append(
                    {
                        "section":
                            "ADS",

                        "ad_group":
                            ad_group_name,

                        "field":
                            "final_url",

                        "error":
                            "FINAL_URL_REQUIRED",
                    }
                )

        return errors

    @staticmethod
    def read_excel(
        file_path: str,
    ) -> dict:

        workbook = load_workbook(
            file_path,
            data_only=True,
        )

        missing_sheets = sorted(
            SearchCampaignService
            .REQUIRED_SHEETS
            .difference(
                set(
                    workbook.sheetnames
                )
            )
        )

        if missing_sheets:

            return {
                "status":
                    "INVALID_TEMPLATE",

                "missing_sheets":
                    missing_sheets,

                "worksheets":
                    workbook.sheetnames,
            }

        campaign = (
            SearchCampaignService
            ._read_campaign(
                workbook
            )
        )

        ad_groups = (
            SearchCampaignService
            ._read_ad_groups(
                workbook,
                campaign.get(
                    "campaign_name"
                ),
            )
        )

        ads = (
            SearchCampaignService
            ._read_ads(
                workbook,
                campaign.get(
                    "campaign_name"
                ),
            )
        )

        validation_errors = []

        validation_errors.extend(
            SearchCampaignService
            ._validate_campaign(
                campaign
            )
        )

        validation_errors.extend(
            SearchCampaignService
            ._validate_ad_groups(
                ad_groups
            )
        )

        validation_errors.extend(
            SearchCampaignService
            ._validate_ads(
                ads
            )
        )

        ad_group_names = {
            ad_group.get(
                "name"
            )
            for ad_group in ad_groups
            if ad_group.get(
                "name"
            )
        }

        ads_without_ad_group = [
            ad.get(
                "ad_group_name"
            )
            for ad in ads
            if ad.get(
                "ad_group_name"
            )
            not in ad_group_names
        ]

        for ad_group_name in (
            ads_without_ad_group
        ):

            validation_errors.append(
                {
                    "section":
                        "ADS",

                    "ad_group":
                        ad_group_name,

                    "error":
                        "AD_GROUP_NOT_FOUND",
                }
            )

        result_status = (
            "READY_FOR_REVIEW"
            if not validation_errors
            else "VALIDATION_FAILED"
        )

        return {
            "status":
                result_status,

            "read_only":
                True,

            "automatic_action":
                False,

            "requires_human_confirmation":
                True,

            "worksheets":
                workbook.sheetnames,

            "campaign":
                campaign,

            "summary": {
                "ad_groups_count":
                    len(ad_groups),

                "ads_count":
                    len(ads),

                "headlines_count":
                    sum(
                        len(
                            ad.get(
                                "headlines",
                                [],
                            )
                        )
                        for ad in ads
                    ),

                "descriptions_count":
                    sum(
                        len(
                            ad.get(
                                "descriptions",
                                [],
                            )
                        )
                        for ad in ads
                    ),

                "validation_errors_count":
                    len(
                        validation_errors
                    ),
            },

            "ad_groups":
                ad_groups,

            "ads":
                ads,

            "validation": {
                "passed":
                    not validation_errors,

                "errors":
                    validation_errors,
            },

            "next_step": (
                "Lire et valider les onglets "
                "Keywords et Sitelinks."
            ),
        }
