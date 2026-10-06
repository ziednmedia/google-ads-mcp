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

        for ad in ads_by
