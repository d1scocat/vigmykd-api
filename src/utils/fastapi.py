from fastapi.responses import JSONResponse

def err(status_code: int, msg: str) -> JSONResponse:
    status = "client-fail" if status_code in range(400, 500) else "server-fail"
    return JSONResponse(
        status_code=status_code,
        content={"status": status, "error": msg}
    )
