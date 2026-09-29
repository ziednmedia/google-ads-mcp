import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {
        "name": "Google Ads MCP",
        "status": "running"
    }

@app.get("/config")
def config():
    return {
        "customer_id": os.getenv("GOOGLE_ADS_CUSTOMER_ID"),
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        "client_id_exists": os.getenv("GOOGLE_ADS_CLIENT_ID") is not None,
        "refresh_token_exists": os.getenv("GOOGLE_ADS_REFRESH_TOKEN") is not None
    }

@app.get("/campaigns")
def campaigns():
    return {
        "customer_id": os.getenv("GOOGLE_ADS_CUSTOMER_ID"),
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        "client_id_exists": os.getenv("GOOGLE_ADS_CLIENT_ID") is not None,
        "refresh_token_exists": os.getenv("GOOGLE_ADS_REFRESH_TOKEN") is not None
    }
