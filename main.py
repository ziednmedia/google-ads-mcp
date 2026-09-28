from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {
        "name": "Google Ads MCP",
        "status": "running"
    }

@app.get("/campaigns")
def get_campaigns():
    return {
        "message": "Google Ads campaigns endpoint"
    }
