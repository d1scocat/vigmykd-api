from fastapi import APIRouter

from vigmykd.routes.v1 import account, auth, key, matchmaking


v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(account.router)
v1_router.include_router(auth.router)
v1_router.include_router(key.router)
v1_router.include_router(matchmaking.router)
