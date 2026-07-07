# Rate Limiter Exercise — Spec

## Overview

Build a FastAPI application that enforces rate limiting on its endpoints using an in-memory sliding window algorithm.

## Goals

- Practice implementing a rate limiter from scratch (no third-party rate-limit libraries)
- Understand sliding window counters
- Use FastAPI middleware or dependencies for clean integration

## Requirements

### Functional

1. **Rate limit per client IP** — each unique IP address gets its own request quota.
2. **Configurable limits** — max requests and window size (in seconds) should be easy to change.
3. **Response headers** — include on every response:
   - `X-RateLimit-Limit` — the maximum number of requests allowed in the window
   - `X-RateLimit-Remaining` — how many requests the client has left in the current window
   - `Retry-After` — seconds until the window resets (only required on `429` responses)
4. **At least two endpoints**:
   - `GET /` — public, rate-limited
   - `GET /status` — returns current rate-limit state for the caller's IP (for debugging)

### Non-Functional

- In-memory storage only (no Redis or external dependencies)
- Python 3.11+, FastAPI, Uvicorn

## Algorithm — Sliding Window Counter

```
window_start = now - window_size
remove all timestamps older than window_start from the client's deque
if len(deque) >= max_requests:
    return 429
else:
    append now to deque
    proceed with request
```

## File Structure

```
rate-limiter-exercise/
├── spec.md          ← this file
├── main.py          ← FastAPI app + rate limiter logic
└── test_main.py     ← tests (optional)
```

## Success Criteria

- [ ] Server starts with `uvicorn main:app --reload`
- [ ] Sending > N requests within the window returns 429
- [ ] Each IP is tracked independently
- [ ] `Retry-After` header is present on 429 responses
- [ ] `X-RateLimit-Limit` header is present on every response
- [ ] `X-RateLimit-Remaining` header is present on every response
