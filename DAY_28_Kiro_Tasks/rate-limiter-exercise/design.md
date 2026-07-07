# Rate Limiter Exercise — Technical Design

## Module Layout

Single-file implementation (`main.py`) with clear internal separation:

```
main.py
├── Config            — constants: MAX_REQUESTS, WINDOW_SECONDS
├── RateLimiter       — core algorithm class
├── rate_limit_check  — FastAPI dependency
├── @app.middleware   — injects headers into every response
├── GET /             — public endpoint
└── GET /status       — debug endpoint
```

---

## Data Structures

### Per-IP request log

```python
from collections import defaultdict, deque

# Key:   client IP string, e.g. "192.168.1.1"
# Value: deque of float timestamps (Unix time, seconds)
request_log: dict[str, deque[float]] = defaultdict(deque)
```

A `deque` is used because:
- `appendleft` / `popleft` are O(1)
- Expired entries are always at the left (oldest first)
- Pruning the window is a simple left-pop loop

### Rate limiter state snapshot (returned to callers)

```python
@dataclass
class RateLimitState:
    limit: int          # MAX_REQUESTS
    remaining: int      # requests left in current window (>= 0)
    retry_after: int    # seconds until oldest request expires (0 if not limited)
    allowed: bool       # True = proceed, False = 429
```

---

## RateLimiter Class

```python
class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int): ...
    def check(self, ip: str) -> RateLimitState: ...
    def peek(self, ip: str) -> RateLimitState: ...  # read-only, for /status
```

### `check(ip)` — called on every rate-limited request

1. `now = time.time()`
2. `window_start = now - window_seconds`
3. Pop from left of `request_log[ip]` while `timestamp < window_start`
4. `count = len(request_log[ip])`
5. If `count >= max_requests`:
   - `retry_after = ceil(request_log[ip][0] + window_seconds - now)`
   - Return `RateLimitState(allowed=False, remaining=0, retry_after=retry_after)`
6. Else:
   - Append `now` to `request_log[ip]`
   - Return `RateLimitState(allowed=True, remaining=max_requests - count - 1, retry_after=0)`

### `peek(ip)` — read-only snapshot for `/status`

Same pruning logic as `check`, but does **not** append a timestamp.

---

## FastAPI Integration

### Dependency — `rate_limit_check`

```python
async def rate_limit_check(request: Request) -> RateLimitState:
    ip = request.client.host
    state = limiter.check(ip)
    if not state.allowed:
        raise HTTPException(status_code=429, ...)
    return state
```

Injected via `Depends(rate_limit_check)` on rate-limited endpoints.

### Middleware — response header injection

```python
@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    response = await call_next(request)
    ip = request.client.host
    state = limiter.peek(ip)
    response.headers["X-RateLimit-Limit"] = str(state.limit)
    response.headers["X-RateLimit-Remaining"] = str(state.remaining)
    if state.retry_after > 0:
        response.headers["Retry-After"] = str(state.retry_after)
    return response
```

The middleware runs **after** the dependency, so `peek` reflects the post-request state.

---

## Endpoints

| Endpoint     | Rate limited | Description                                      |
|--------------|-------------|--------------------------------------------------|
| `GET /`      | Yes          | Returns `{"message": "Hello!"}` or 429          |
| `GET /status`| No           | Returns the caller's current rate-limit snapshot |

`/status` is intentionally not rate-limited so clients can always query their state.

---

## Error Handling

| Scenario                        | Behaviour                                                    |
|---------------------------------|--------------------------------------------------------------|
| Rate limit exceeded             | `429 Too Many Requests`, body `{"detail": "Rate limit exceeded"}`, `Retry-After` header |
| `request.client` is `None`      | Fall back to IP `"unknown"` — all such clients share a bucket |
| Concurrent requests (same IP)   | Python's GIL protects the in-memory deque for single-process Uvicorn; acceptable for this exercise |

---

## Configuration

```python
MAX_REQUESTS: int = 10   # requests per window
WINDOW_SECONDS: int = 60 # window size in seconds
```

Defined as module-level constants at the top of `main.py` for easy adjustment.

---

## Limitations (out of scope)

- No persistence — restarting the server resets all counters
- No distributed support — single process only
- No per-route limits — all rate-limited endpoints share the same quota per IP
