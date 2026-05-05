from fastapi import APIRouter
from routes.v1.account import change_password, delete, register


router = APIRouter(prefix="/account")

router.include_router(change_password.router)
router.include_router(delete.router)
router.include_router(register.router)
