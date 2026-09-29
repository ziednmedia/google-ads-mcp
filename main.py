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
        "version": "2026-09-28-v2"
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

@app.get("/campaign-performance")
def campaign_performance():

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
                campaign.name,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM campaign
            WHERE segments.date DURING LAST_30_DAYS
        """

        response = ga_service.search(
            customer_id=os.getenv("GOOGLE_ADS_CUSTOMER_ID"),
            query=query,
        )

        data = []

        for row in response:

            cost = row.metrics.cost_micros / 1000000
            clicks = row.metrics.clicks
            conversions = row.metrics.conversions
            conversion_value = row.metrics.conversions_value

            cpa = None
            roas = None

            if conversions > 0:
                cpa = round(cost / conversions, 2)

            if cost > 0:
                roas = round(conversion_value / cost, 2)

            data.append({
                "campaign_id": row.campaign.id,
                "campaign_name": row.campaign.name,
                "impressions": row.metrics.impressions,
                "clicks": clicks,
                "cost": round(cost, 2),
                "conversions": round(conversions, 2),
                "conversion_value": round(conversion_value, 2),
                "cpa": cpa,
                "roas": roas
            })

        return data

    except Exception as e:
        return {
            "error": str(e)
        }

@app.get("/top-campaigns")
def top_campaigns():

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
                campaign.name,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM campaign
            WHERE segments.date DURING LAST_30_DAYS
        """

        response = ga_service.search(
            customer_id=os.getenv("GOOGLE_ADS_CUSTOMER_ID"),
            query=query,
        )

        data = []

        for row in response:

            cost = row.metrics.cost_micros / 1000000
            conversions = row.metrics.conversions
            conversion_value = row.metrics.conversions_value

            cpa = None
            roas = None

            if conversions > 0:
                cpa = round(cost / conversions, 2)

            if cost > 0:
                roas = round(conversion_value / cost, 2)

            data.append({
                "campaign_id": row.campaign.id,
                "campaign_name": row.campaign.name,
                "cost": round(cost, 2),
                "conversions": round(conversions, 2),
                "conversion_value": round(conversion_value, 2),
                "cpa": cpa,
                "roas": roas
            })

        filtered = [
            c for c in data
            if c["roas"] is not None
        ]

        filtered.sort(
            key=lambda x: x["roas"],
            reverse=True
        )

        return filtered[:10]

    except Exception as e:
        return {
            "error": str(e)
        }

@app.get("/keywords")
def keywords():

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
                campaign.name,
                ad_group.name,
                ad_group_criterion.keyword.text,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions
            FROM keyword_view
            WHERE segments.date DURING LAST_30_DAYS
        """

        response = ga_service.search(
            customer_id=os.getenv("GOOGLE_ADS_CUSTOMER_ID"),
            query=query,
        )

        data = []

        for row in response:

            cost = row.metrics.cost_micros / 1000000
            conversions = row.metrics.conversions

            cpa = None

            if conversions > 0:
                cpa = round(cost / conversions, 2)

            data.append({
                "campaign": row.campaign.name,
                "ad_group": row.ad_group.name,
                "keyword": row.ad_group_criterion.keyword.text,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "cost": round(cost, 2),
                "conversions": round(conversions, 2),
                "cpa": cpa
            })

        return data

    except Exception as e:
        return {
            "error": str(e)
        }
@app.get("/search-terms")
def search_terms():

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
                campaign.name,
                ad_group.name,
                search_term_view.search_term,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions
            FROM search_term_view
            WHERE segments.date DURING LAST_30_DAYS
        """

        response = ga_service.search(
            customer_id=os.getenv("GOOGLE_ADS_CUSTOMER_ID"),
            query=query,
        )

        data = []

        for row in response:

            cost = row.metrics.cost_micros / 1000000
            conversions = row.metrics.conversions

            cpa = None

            if conversions > 0:
                cpa = round(cost / conversions, 2)

            data.append({
                "campaign": row.campaign.name,
                "ad_group": row.ad_group.name,
                "search_term": row.search_term_view.search_term,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "cost": round(cost, 2),
                "conversions": round(conversions, 2),
                "cpa": cpa
            })

        return data

    except Exception as e:
        return {
            "error": str(e)
        }
