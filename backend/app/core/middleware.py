from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time
import uuid
import logging

logger = logging.getLogger(__name__)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Processing-Time-Ms"] = str(duration_ms)
        logger.info(
            f"{request.method} {request.url.path} "
            f"status={response.status_code} duration={duration_ms}ms "
            f"request_id={request_id}"
        )
        return response


class AuditLogMiddleware(BaseHTTPMiddleware):
    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.method in self.WRITE_METHODS and "/api/" in request.url.path:
            logger.info(
                f"AUDIT | method={request.method} path={request.url.path} "
                f"status={response.status_code} "
                f"client={request.client.host if request.client else 'unknown'}"
            )
        return response
