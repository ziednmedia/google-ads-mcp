from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {
        "name": "Google Ads MCP",
        "status": "running"
    }

@app.get("/campaigns")
def campaigns():
    return {
        "message": "campaign endpoint ready"
    }
