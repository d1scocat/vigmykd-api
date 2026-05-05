from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from routes.v1.auth.login import models


router = APIRouter()
security = HTTPBearer()


@router.post("/login")
async def login(
    query: models.LoginQuery,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # credentials.scheme -> "Bearer"
    # credentials.credentials -> "<token>"
    pass
