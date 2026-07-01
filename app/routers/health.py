from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "ortoolsVersion": "9.11+",
        "mockMode": settings.MOCK_MODE,
    }
