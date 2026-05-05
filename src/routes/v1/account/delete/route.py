from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from routes.v1.account.delete import models


router = APIRouter()
security = HTTPBearer()


@router.delete("/delete")
async def delete(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # credentials.scheme -> "Bearer"
    # credentials.credentials -> "<token>"
    pass


@router.post("/delete/confirm")
async def confirm(
    query: models.ConfirmQuery,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    pass
