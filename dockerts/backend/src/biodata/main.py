"""FastAPI application factory."""

from __future__ import annotations

from contextlib import suppress
from typing import Annotated, Any, cast

from fastapi import Depends, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import StreamingResponse

from biodata import service
from biodata.api.routes import router as api_router
from biodata.config import Settings, get_settings
from biodata.db import get_engine, get_session, ping, session_scope
from biodata.logging import configure_logging
from biodata.models import Base
from biodata.schemas import RequestResponseCreate

API_PREFIX = "/api/v1"


class RequestResponseLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that intercepts requests and responses, writing them to SQLite database."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path in ("/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        req_body_bytes = await request.body()
        req_body_str = req_body_bytes.decode("utf-8", errors="replace") if req_body_bytes else None

        response = cast(StreamingResponse, await call_next(request))

        resp_body_bytes = b""
        async for chunk in response.body_iterator:
            resp_body_bytes += chunk.encode() if isinstance(chunk, str) else bytes(chunk)

        new_response = Response(
            content=resp_body_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

        resp_body_str = (
            resp_body_bytes.decode("utf-8", errors="replace") if resp_body_bytes else None
        )

        if path != f"{API_PREFIX}/request-responses":
            try:
                with session_scope() as session:
                    service.log_request_response(
                        session,
                        RequestResponseCreate(
                            method=request.method,
                            path=path,
                            status_code=response.status_code,
                            request_body=req_body_str,
                            response_body=resp_body_str,
                        ),
                    )
            except Exception:
                pass

        return new_response


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    with suppress(Exception):
        Base.metadata.create_all(bind=get_engine())

    app = FastAPI(
        title="biodata",
        version="0.1.0",
        summary="Biodata records service",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestResponseLoggingMiddleware)

    @app.get("/health", tags=["ops"])
    def health(
        response: Response,
        session: Annotated[Session, Depends(get_session)],
    ) -> dict[str, Any]:
        """Report service and database liveness."""
        healthy = ping(session)
        if not healthy:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "error", "database": "error"}
        return {"status": "ok", "database": "ok"}

    app.include_router(api_router, prefix=API_PREFIX)
    return app


app = create_app()
