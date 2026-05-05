from fastapi import APIRouter

from routes.v1 import account, auth


v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(account.router)
v1_router.include_router(auth.router)
