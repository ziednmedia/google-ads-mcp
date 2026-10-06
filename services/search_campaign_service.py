from openpyxl import load_workbook


class SearchCampaignService:

    @staticmethod
    def health():

        return {
            "status": "SUCCESS",
            "module": "SEARCH"
        }

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

        return {
            "worksheets":
                workbook.sheetnames,

            "campaign":
                campaign,

            "ad_groups":
                ad_groups,
        }

