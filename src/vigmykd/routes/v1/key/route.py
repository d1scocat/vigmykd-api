from fastapi import APIRouter

from vigmykd.routes.v1.key import public


router = APIRouter(prefix="/key")

router.include_router(public.router)
