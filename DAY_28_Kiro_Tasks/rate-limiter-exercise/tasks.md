# Rate Limiter Exercise — Implementation Tasks

## 1. Project Setup
- [ ] 1.1 Create `main.py` with file-level docstring and imports
- [ ] 1.2 Define `MAX_REQUESTS` and `WINDOW_SECONDS` constants
- [ ] 1.3 Create `requirements.txt` (fastapi, uvicorn)

## 2. Core Data Structures
- [ ] 2.1 Define `RateLimitState` dataclass with fields: `limit`, `remaining`, `retry_after`, `allowed`
- [ ] 2.2 Define `request_log` as `defaultdict(deque)` inside `RateLimiter`

## 3. RateLimiter Class
- [ ] 3.1 Implement `__init__(self, max_requests, window_seconds)`
- [ ] 3.2 Implement `_prune(self, ip, now)` — shared helper that removes expired timestamps
- [ ] 3.3 Implement `check(self, ip)` — prune, enforce limit, append timestamp, return `RateLimitState`
- [ ] 3.4 Implement `peek(self, ip)` — prune, return state without appending timestamp
- [ ] 3.5 Instantiate a module-level `limiter = RateLimiter(MAX_REQUESTS, WINDOW_SECONDS)`

## 4. FastAPI App & Middleware
- [ ] 4.1 Create `app = FastAPI()`
- [ ] 4.2 Implement `rate_limit_check` dependency — calls `limiter.check()`, raises `HTTPException(429)` if not allowed
- [ ] 4.3 Implement `add_rate_limit_headers` middleware — calls `limiter.peek()` after response, sets `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `Retry-After` (429 only)
- [ ] 4.4 Handle `request.client is None` edge case in both dependency and middleware (fall back to `"unknown"`)

## 5. Endpoints
- [ ] 5.1 Implement `GET /` with `Depends(rate_limit_check)` — returns `{"message": "Hello!"}`
- [ ] 5.2 Implement `GET /status` (no rate limit) — returns JSON snapshot from `limiter.peek()`

## 6. Tests (`test_main.py`)
- [ ] 6.1 Install `httpx` and `pytest` (required for FastAPI `TestClient`)
- [ ] 6.2 Test: requests within limit return 200 with correct headers
- [ ] 6.3 Test: request exceeding limit returns 429 with `Retry-After` header
- [ ] 6.4 Test: `X-RateLimit-Remaining` decrements correctly across requests
- [ ] 6.5 Test: `GET /status` always returns 200 (not rate-limited)
- [ ] 6.6 Test: two different IPs have independent counters

## 7. Verification
- [ ] 7.1 Run `uvicorn main:app --reload` and confirm server starts
- [ ] 7.2 Run `pytest test_main.py -v` — all tests pass
- [ ] 7.3 Manual smoke test with `curl` — hit limit and confirm 429 + headers
- [ ] 7.4 Update success criteria checkboxes in `spec.md`
