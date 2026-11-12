"""Application factory and ASGI entrypoint (`uvicorn app.main:app`)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_route_provider, get_weather_service
from app.api.error_handlers import register_error_handlers
from app.api.v1 import api_router
from app.core.config import Settings, get_settings
from app.db import build_engine, init_db
from app.mcp_server import build_mcp_http_app, build_mcp_registry, build_mcp_server


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    # Built here, not at import time, so each app (and each test app) gets its own engine.
    engine = build_engine(settings.database_url)
    # The MCP server (Streamable HTTP at /mcp) shares the process-wide providers with the API.
    mcp_server = build_mcp_server(
        build_mcp_registry(get_route_provider(), get_weather_service(), engine)
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        init_db(engine)
        async with mcp_server.session_manager.run():
            yield
        engine.dispose()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.state.engine = engine
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        # MCP clients in the browser must read the session id the server assigns.
        expose_headers=["mcp-session-id"],
    )
    register_error_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)
    app.router.routes.extend(build_mcp_http_app(mcp_server, settings).routes)
    return app


app = create_app()
