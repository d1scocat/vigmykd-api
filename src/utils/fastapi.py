from fastapi import Request
from fastapi.responses import JSONResponse


def err(status_code: int, msg: str) -> JSONResponse:
    status = "client-fail" if status_code in range(400, 500) else "server-fail"
    return JSONResponse(
        status_code=status_code,
        content={"status": status, "error": msg}
    )


def get_real_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    return request.client.host if request.client else ""
