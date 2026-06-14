from fastapi import APIRouter

from vigmykd.routes.v1.matchmaking import start


router = APIRouter(prefix="/matchmaking")

router.include_router(start.router)
