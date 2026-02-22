from fastapi import APIRouter

from .transfers import router as transfers_router
from .users import router as users_router
from .wallets import router as wallet_router

router = APIRouter()

router.include_router(transfers_router)
router.include_router(wallet_router)
router.include_router(users_router)
