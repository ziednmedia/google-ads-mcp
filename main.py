import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {
        "name": "Google Ads MCP",
        "status": "running"
    }


@app.get("/version")
def version():
    return {
        "version": "2026-09-28-v1"
    }
@app.get("/config")
def config():
    return {
        "customer_id": os.getenv("GOOGLE_ADS_CUSTOMER_ID"),
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        "client_id_exists": os.getenv("GOOGLE_ADS_CLIENT_ID") is not None,
        "refresh_token_exists": os.getenv("GOOGLE_ADS_REFRESH_TOKEN") is not None
    }

from google.ads.googleads.client import GoogleAdsClient

@app.get("/campaigns")
def campaigns():

    config = {
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        "use_proto_plus": True
    }

    try:
        client = GoogleAdsClient.load_from_dict(config)

        ga_service = client.get_service("GoogleAdsService")

        query = """
            SELECT
                campaign.id,
                campaign.name
            FROM campaign
            LIMIT 20
        """

        response = ga_service.search(
            customer_id=os.getenv("GOOGLE_ADS_CUSTOMER_ID"),
            query=query,
        )

        campaigns = []

        for row in response:
            campaigns.append({
                "id": row.campaign.id,
                "name": row.campaign.name
            })

        return campaigns

    except Exception as e:
        return {
            "error": str(e)
        }


