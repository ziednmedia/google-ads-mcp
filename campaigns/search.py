from fastapi import APIRouter

router = APIRouter(
    prefix="/campaigns/search",
    tags=["Search Campaigns"]
)


@router.get("/health")
def search_health():
    return {
        "status": "SUCCESS",
        "module": "SEARCH"
    }
