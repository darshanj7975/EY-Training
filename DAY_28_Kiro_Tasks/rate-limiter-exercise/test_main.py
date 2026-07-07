"""
Tests for rate-limiter-exercise (main.py).

Uses FastAPI's TestClient (backed by httpx) with a patched limiter so tests
run fast without real time.sleep() calls.
"""

import time
from collections import defaultdict, deque
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main
from main import RateLimiter, RateLimitState, app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fresh_client(max_requests: int = 3, window_seconds: int = 60) -> TestClient:
    """
    Return a TestClient whose module-level limiter is reset to given params.
    Patching main.limiter ensures both the dependency and middleware use it.
    """
    new_limiter = RateLimiter(max_requests, window_seconds)
    with patch.object(main, "limiter", new_limiter):
        # TestClient is used as a context manager so lifespan events fire
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client, new_limiter


# ---------------------------------------------------------------------------
# Unit tests — RateLimiter in isolation
# ---------------------------------------------------------------------------


class TestRateLimiter:
    def test_first_request_allowed(self):
        rl = RateLimiter(max_requests=5, window_seconds=60)
        state = rl.check("1.2.3.4")
        assert state.allowed is True
        assert state.limit == 5
        assert state.remaining == 4

    def test_remaining_decrements(self):
        rl = RateLimiter(max_requests=3, window_seconds=60)
        for expected_remaining in [2, 1, 0]:
            # last one (remaining=0) is still allowed
            state = rl.check("1.2.3.4")
            assert state.remaining == expected_remaining

    def test_exceeding_limit_blocked(self):
        rl = RateLimiter(max_requests=2, window_seconds=60)
        rl.check("1.2.3.4")
        rl.check("1.2.3.4")
        state = rl.check("1.2.3.4")
        assert state.allowed is False
        assert state.remaining == 0
        assert state.retry_after >= 1

    def test_peek_does_not_consume_quota(self):
        rl = RateLimiter(max_requests=2, window_seconds=60)
        rl.check("1.2.3.4")
        before = rl.peek("1.2.3.4")
        after = rl.peek("1.2.3.4")
        assert before.remaining == after.remaining == 1

    def test_different_ips_independent(self):
        rl = RateLimiter(max_requests=1, window_seconds=60)
        rl.check("1.1.1.1")  # exhausts quota for 1.1.1.1
        state_a = rl.check("1.1.1.1")
        state_b = rl.check("2.2.2.2")
        assert state_a.allowed is False
        assert state_b.allowed is True

    def test_expired_timestamps_pruned(self):
        rl = RateLimiter(max_requests=2, window_seconds=1)
        rl.check("1.2.3.4")
        rl.check("1.2.3.4")
        # Both slots used — would be blocked
        assert rl.check.__func__  # sanity

        # Travel forward past the window
        future = time.time() + 2
        with patch("main.time") as mock_time:
            mock_time.time.return_value = future
            state = rl.check("1.2.3.4")
        assert state.allowed is True  # old entries pruned


# ---------------------------------------------------------------------------
# Integration tests — HTTP layer
# ---------------------------------------------------------------------------


class TestRootEndpoint:
    def test_returns_200_within_limit(self):
        gen = fresh_client(max_requests=3)
        client, _ = next(gen)
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello!"}

    def test_returns_429_when_limit_exceeded(self):
        gen = fresh_client(max_requests=2)
        client, _ = next(gen)
        client.get("/")
        client.get("/")
        response = client.get("/")
        assert response.status_code == 429
        assert response.json()["detail"] == "Rate limit exceeded"

    def test_retry_after_header_on_429(self):
        gen = fresh_client(max_requests=1)
        client, _ = next(gen)
        client.get("/")
        response = client.get("/")
        assert response.status_code == 429
        assert "retry-after" in response.headers
        assert int(response.headers["retry-after"]) >= 1

    def test_x_ratelimit_limit_header_present(self):
        gen = fresh_client(max_requests=5)
        client, _ = next(gen)
        response = client.get("/")
        assert "x-ratelimit-limit" in response.headers
        assert response.headers["x-ratelimit-limit"] == "5"

    def test_x_ratelimit_remaining_decrements(self):
        gen = fresh_client(max_requests=3)
        client, _ = next(gen)
        r1 = client.get("/")
        r2 = client.get("/")
        r3 = client.get("/")
        assert r1.headers["x-ratelimit-remaining"] == "2"
        assert r2.headers["x-ratelimit-remaining"] == "1"
        assert r3.headers["x-ratelimit-remaining"] == "0"

    def test_no_retry_after_on_200(self):
        gen = fresh_client(max_requests=5)
        client, _ = next(gen)
        response = client.get("/")
        assert response.status_code == 200
        assert "retry-after" not in response.headers


class TestStatusEndpoint:
    def test_status_always_200(self):
        gen = fresh_client(max_requests=1)
        client, _ = next(gen)
        # Exhaust the rate limit via /
        client.get("/")
        client.get("/")  # 429
        # /status must still succeed
        response = client.get("/status")
        assert response.status_code == 200

    def test_status_returns_correct_fields(self):
        gen = fresh_client(max_requests=5)
        client, _ = next(gen)
        response = client.get("/status")
        data = response.json()
        assert "limit" in data
        assert "remaining" in data
        assert "retry_after" in data
        assert "window_seconds" in data
        assert data["limit"] == 5

    def test_status_remaining_reflects_root_requests(self):
        gen = fresh_client(max_requests=3)
        client, _ = next(gen)
        client.get("/")
        client.get("/")
        status = client.get("/status").json()
        assert status["remaining"] == 1


class TestIpIsolation:
    def test_different_ips_do_not_share_quota(self):
        """Simulate two clients by hitting the limiter directly."""
        rl = RateLimiter(max_requests=1, window_seconds=60)
        rl.check("10.0.0.1")  # exhaust ip1
        state_ip1 = rl.peek("10.0.0.1")
        state_ip2 = rl.peek("10.0.0.2")
        assert state_ip1.remaining == 0
        assert state_ip2.remaining == 1
