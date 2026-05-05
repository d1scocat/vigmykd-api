from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from routes.router import v1_router


@asynccontextmanager
async def lifespan(api: FastAPI):
    # api.state.(add variable) = value

    yield


def make_app() -> FastAPI:
    app = FastAPI(
        title="vigmykd REST API",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router)

    return app


app = make_app()

# Launch with:
# uvicorn entrypoint:app --workers <amount of workers>
