from openpyxl import load_workbook


class SearchCampaignService:

    @staticmethod
    def health():

        return {
            "status": "SUCCESS",
            "module": "SEARCH"
        }
# -------------------------------------
# READ EXCEL
# -------------------------------------
    @staticmethod
    def read_excel(
        file_path: str,
    ):

        workbook = load_workbook(
            file_path,
            data_only=True,
        )

        account_sheet = workbook[
            "Account & Campaign"
        ]

        campaign = {
            "account_name":
                account_sheet["C4"].value,

            "customer_id":
                account_sheet["C5"].value,

            "campaign_name":
                account_sheet["C6"].value,

            "objective":
                account_sheet["C7"].value,

            "daily_budget":
                account_sheet["C8"].value,

            "currency":
                account_sheet["C9"].value,

            "language":
                account_sheet["C10"].value,
           
            "locations": [
                location.strip()
                for location in (
                account_sheet["C11"].value or ""
                ).split(";")
                if location.strip()
            ],

            "network":
                account_sheet["C12"].value,

            "bidding_strategy":
                account_sheet["C13"].value,

            "start_date":
                str(
                    account_sheet["C14"].value
                ),

            "end_date":
                str(
                    account_sheet["C15"].value
                ),

            "status":
                account_sheet["C16"].value,

            "label":
                account_sheet["C17"].value,
        }

# -------------------------------------
# AD GROUPS
# -------------------------------------

        ad_groups_sheet = workbook[
            "Ad Groups"
        ]

        ad_groups = []

        for row in range(
            4,
            ad_groups_sheet.max_row + 1,
        ):

            campaign_name = (
                ad_groups_sheet[
                    f"A{row}"
                ].value
            )

            if not campaign_name:
                continue

            ad_groups.append(
                {
                    "campaign_name":
                        campaign_name,

                    "name":
                        ad_groups_sheet[
                            f"B{row}"
                        ].value,

                    "final_url":
                        ad_groups_sheet[
                            f"C{row}"
                        ].value,

                    "path1":
                        ad_groups_sheet[
                            f"D{row}"
                        ].value,

                    "path2":
                        ad_groups_sheet[
                            f"F{row}"
                        ].value,

                    "utm_source":
                        ad_groups_sheet[
                            f"H{row}"
                        ].value,

                    "utm_medium":
                        ad_groups_sheet[
                            f"I{row}"
                        ].value,

                    "utm_campaign":
                        ad_groups_sheet[
                            f"J{row}"
                        ].value,

                    "utm_term":
                        ad_groups_sheet[
                            f"K{row}"
                        ].value,

                    "utm_content":
                        ad_groups_sheet[
                            f"L{row}"
                        ].value,
                }
            )

# ==========================================
# ADS
# ==========================================

        ads_sheet = workbook[
            "Ads"
        ]

        ads = {}

        for row in range(
            4,
            ads_sheet.max_row + 1,
        ):

            campaign_name = (
                ads_sheet[
                    f"A{row}"
                ].value
            )

            ad_group_name = (
                ads_sheet[
                    f"B{row}"
                ].value
            )

            if (
                not campaign_name
                or not ad_group_name
            ):
                continue

            headline = (
                ads_sheet[
                    f"C{row}"
                ].value
            )

            description = (
                ads_sheet[
                    f"E{row}"
                ].value
            )

            key = (
                campaign_name,
                ad_group_name,
            )

            if key not in ads:

                ads[key] = {
                    "campaign_name":
                        campaign_name,

                    "ad_group_name":
                        ad_group_name,

                    "headlines":
                        [],

                    "descriptions":
                        [],

                    "path1":
                        ads_sheet[
                            f"G{row}"
                        ].value,

                    "path2":
                        ads_sheet[
                            f"I{row}"
                        ].value,

                    "final_url":
                        ads_sheet[
                            f"K{row}"
                        ].value,

                    "label":
                        ads_sheet[
                            f"L{row}"
                        ].value,
                }

            if headline:

                ads[key][
                    "headlines"
                ].append(
                    str(
                        headline
                    ).strip()
                )

            if description:

                ads[key][
                    "descriptions"
                ].append(
                    str(
                        description
                    ).strip()
                )

        ads_list = []

        for ad in ads.values():

            ad["headlines"] = list(
                dict.fromkeys(
                    ad["headlines"]
                )
            )

            ad["descriptions"] = list(
                dict.fromkeys(
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

            ads_list.append(
                ad
            )


        
        return {
            "worksheets":
                workbook.sheetnames,

            "campaign":
                campaign,

            "ad_groups":
                ad_groups,
            
            "ads":
                ads_list,
        }
        return {
            "worksheets":
                workbook.sheetnames,

            "campaign":
                campaign,

            "ad_groups":
                ad_groups,

            "ads":
                ads_list,

            "summary": {
                "ad_groups_count":
                    len(ad_groups),

            "ads_count":
                    len(ads_list),

            "headlines_count":
                    sum(
                        ad[
                            "headlines_count"
                          ]
                        for ad in ads_list
                    ),

            "descriptions_count":
                    sum(
                        ad[
                            "descriptions_count"
                          ]
                        for ad in ads_list
                    ),
            },
        }

