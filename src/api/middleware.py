"""
FastAPI middleware — request logging, rate limiting, and API key auth.
"""
import time
import logging
import os
from collections import defaultdict
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

API_KEY = os.getenv("API_KEY", "")          # set in .env to enforce auth
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "100"))  # requests per minute per IP


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status code, and duration."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            f"{request.method} {request.url.path} "
            f"→ {response.status_code} ({duration_ms}ms)"
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter. Replace with Redis for multi-worker production."""

    def __init__(self, app, requests_per_minute: int = RATE_LIMIT):
        super().__init__(app)
        self.rpm = requests_per_minute
        self._counts: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Skip health check endpoints
        if request.url.path in ("/health", "/stats", "/feedback", "/report", "/alerts"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = now - 60  # 1-minute window

        # Clean old timestamp entries out of memory
        self._counts[client_ip] = [
            t for t in self._counts[client_ip] if t > window
        ]

        # Use JSONResponse directly instead of raising an HTTPException inside dispatch
        if len(self._counts[client_ip]) >= self.rpm:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded: {self.rpm} requests per minute maximum allowed."}
            )

        self._counts[client_ip].append(now)
        return await call_next(request)


def require_api_key(request: Request):
    """FastAPI dependency — enforces API key header if API_KEY is set."""
    if not API_KEY:
        return  # no key configured → open access
    key = request.headers.get("X-API-Key", "")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
