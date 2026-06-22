from fastapi import APIRouter

from vigmykd.routes.v1.matchmaking import end
from vigmykd.routes.v1.matchmaking import start


router = APIRouter(prefix="/matchmaking")

router.include_router(end.router)
router.include_router(start.router)
