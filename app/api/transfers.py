from fastapi import APIRouter

router = APIRouter(prefix="/transfers", tags=["transfers"])

@router.get("/ping")
def ping():
    return {"ping": "ok"}
