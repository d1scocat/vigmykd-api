from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from routes.v1.account.change_password import models


router = APIRouter()
security = HTTPBearer()


@router.patch("/change-password")
async def change_password(
    query: models.ChangePasswordQuery,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # credentials.scheme -> "Bearer"
    # credentials.credentials -> "<token>"
    pass
