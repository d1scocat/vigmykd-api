from fastapi import APIRouter

from vigmykd.routes.v1.auth import diagnostic, login, logout


router = APIRouter(prefix="/auth")

router.include_router(diagnostic.router)
router.include_router(login.router)
router.include_router(logout.router)
