"""
Rate Limiter Exercise
=====================
FastAPI application with an in-memory sliding window rate limiter.

Configuration:
  MAX_REQUESTS   — maximum requests allowed per IP per window
  WINDOW_SECONDS — rolling window size in seconds
"""

import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_REQUESTS: int = 10   # requests allowed per window
WINDOW_SECONDS: int = 60  # window size in seconds

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RateLimitState:
    """Snapshot of rate-limit state for a single IP."""

    limit: int       # maximum requests allowed in the window
    remaining: int   # requests remaining in the current window (>= 0)
    retry_after: int # seconds until the oldest request expires (0 if not limited)
    allowed: bool    # True → proceed with request; False → return 429


# ---------------------------------------------------------------------------
# RateLimiter class
# ---------------------------------------------------------------------------


class RateLimiter:
    """
    Sliding window rate limiter backed by an in-memory deque per IP.

    Thread safety: relies on the CPython GIL for single-process Uvicorn.
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Key: client IP string; Value: deque of float Unix timestamps
        self._log: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, ip: str, now: float) -> None:
        """Remove timestamps outside the current window (oldest are on the left)."""
        window_start = now - self.window_seconds
        log = self._log[ip]
        while log and log[0] < window_start:
            log.popleft()

    def check(self, ip: str) -> RateLimitState:
        """
        Check and record a request for *ip*.

        Mutating: appends the current timestamp if the request is allowed.
        Returns a RateLimitState indicating whether to allow or block.
        """
        now = time.time()
        self._prune(ip, now)
        log = self._log[ip]
        count = len(log)

        if count >= self.max_requests:
            # Oldest request is log[0]; it will expire at log[0] + window_seconds
            retry_after = math.ceil(log[0] + self.window_seconds - now)
            return RateLimitState(
                limit=self.max_requests,
                remaining=0,
                retry_after=max(retry_after, 1),
                allowed=False,
            )

        log.append(now)
        return RateLimitState(
            limit=self.max_requests,
            remaining=self.max_requests - count - 1,
            retry_after=0,
            allowed=True,
        )

    def peek(self, ip: str) -> RateLimitState:
        """
        Read-only snapshot of rate-limit state for *ip*.

        Non-mutating: prunes expired entries but does NOT append a timestamp.
        Used by the middleware and /status endpoint.
        """
        now = time.time()
        self._prune(ip, now)
        log = self._log[ip]
        count = len(log)

        if count >= self.max_requests:
            retry_after = math.ceil(log[0] + self.window_seconds - now)
            return RateLimitState(
                limit=self.max_requests,
                remaining=0,
                retry_after=max(retry_after, 1),
                allowed=False,
            )

        return RateLimitState(
            limit=self.max_requests,
            remaining=self.max_requests - count,
            retry_after=0,
            allowed=True,
        )


# Module-level limiter instance shared across all requests
limiter = RateLimiter(MAX_REQUESTS, WINDOW_SECONDS)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(title="Rate Limiter Exercise")


def _get_ip(request: Request) -> str:
    """Return the client IP, falling back to 'unknown' if not available."""
    if request.client is None:
        return "unknown"
    return request.client.host


# ---------------------------------------------------------------------------
# Dependency — enforces rate limit, raises 429 if exceeded
# ---------------------------------------------------------------------------


async def rate_limit_check(request: Request) -> RateLimitState:
    """FastAPI dependency that enforces the rate limit for the calling IP."""
    ip = _get_ip(request)
    state = limiter.check(ip)
    if not state.allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(state.retry_after)},
        )
    return state


# ---------------------------------------------------------------------------
# Middleware — injects rate-limit headers into every response
# ---------------------------------------------------------------------------


@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    """
    Attach X-RateLimit-* headers to every response.

    Runs after the route handler, so peek() reflects the post-request state.
    Retry-After is only added on 429 responses.
    """
    response = await call_next(request)
    ip = _get_ip(request)
    state = limiter.peek(ip)

    response.headers["X-RateLimit-Limit"] = str(state.limit)
    response.headers["X-RateLimit-Remaining"] = str(state.remaining)
    if response.status_code == 429 and state.retry_after > 0:
        response.headers["Retry-After"] = str(state.retry_after)

    return response


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/")
async def root(state: RateLimitState = Depends(rate_limit_check)):
    """Public endpoint — rate limited per client IP."""
    return {"message": "Hello!"}


@app.get("/status")
async def status(request: Request):
    """
    Debug endpoint — returns the caller's current rate-limit snapshot.
    Not rate-limited, so clients can always check their quota.
    """
    ip = _get_ip(request)
    state = limiter.peek(ip)
    return {
        "ip": ip,
        "limit": state.limit,
        "remaining": state.remaining,
        "retry_after": state.retry_after,
        "window_seconds": WINDOW_SECONDS,
    }
