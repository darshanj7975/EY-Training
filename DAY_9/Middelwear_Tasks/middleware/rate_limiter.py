from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from collections import defaultdict
from datetime import datetime
from metrics import RATE_LIMIT_HITS
from metrics import RATE_LIMIT_HITS

REQUEST_LIMIT = 100
WINDOW_SIZE = 60  # seconds

request_store = defaultdict(list)


class RateLimiterMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        client_ip = request.client.host
        current_time = datetime.now().timestamp()

        # Get request history for this IP
        timestamps = request_store[client_ip]

        # Keep only timestamps inside window
        request_store[client_ip] = [
            ts for ts in timestamps
            if current_time - ts < WINDOW_SIZE
        ]

        timestamps = request_store[client_ip]

        # Check limit
        if len(timestamps) >= REQUEST_LIMIT:

            RATE_LIMIT_HITS.inc()

            oldest_request = timestamps[0]
            retry_after = WINDOW_SIZE - (
                current_time - oldest_request
            )

            return JSONResponse(
                status_code=429,
                content={
                    "message":
                    "Too Many Requests. Please try again later."
                },
                headers={
                    "Retry-After": str(int(retry_after))
                }
            )

        timestamps.append(current_time)

        response = await call_next(request)

        return response