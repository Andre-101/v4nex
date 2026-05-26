from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/_v4nex/health")
def internal_health() -> dict[str, str]:
    return {"status": "ok"}
