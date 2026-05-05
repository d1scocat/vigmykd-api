from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from routes.v1.account.register import models


router = APIRouter()
security = HTTPBearer()


@router.post("/register")
async def register(
    query: models.RegisterQuery,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # credentials.scheme -> "Bearer"
    # credentials.credentials -> "<token>"
    pass


@router.post("/register/confirm")
async def confirm(
    query: models.ConfirmQuery,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    pass
