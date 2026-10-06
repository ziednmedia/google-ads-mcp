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

        return {
            "worksheets":
                workbook.sheetnames
        }
