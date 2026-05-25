import logging
import time

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware

from log import setup as setup_log
from routes.router import v1_router
from start import DependencyManager, TaskManager
from utils import err


logger = logging.getLogger("vigmykd")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start = time.monotonic()

    setup_log.setup()

    dependencies = DependencyManager(app)
    tasks = TaskManager(dependencies)

    await dependencies.init()
    await tasks.init(start=True)

    elapsed = time.monotonic() - start
    logger.info(f"⏱️ vigmykd REST API successfully started in {elapsed:.4f}s\n")

    yield

    halt_start = time.monotonic()

    await dependencies.cleanup()
    await tasks.cleanup()

    halt_elapsed = time.monotonic() - halt_start
    logger.info(f"⏱️ vigmykd REST API successfully stopped in {halt_elapsed:.4f}s")


def make_app() -> FastAPI:
    app = FastAPI(
        title="vigmykd REST API",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://vigmykd.runderscore.com"
        ],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.include_router(v1_router)

    return app


app = make_app()


@app.middleware("http")
async def handle_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except HTTPException as ex:
        return err(status_code=ex.status_code, msg=ex.detail)
    except Exception as ex:
        logger.error(f"❌ Uncaught exception: {ex}", exc_info=True)
        return err(status_code=500, msg=f"{ex}")

# Launch with:
# uvicorn entrypoint:app --workers <amount of workers>
