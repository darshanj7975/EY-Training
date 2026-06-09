
from prometheus_client import Counter

RATE_LIMIT_HITS = Counter(
    "rate_limit_hits_total",
    "Number of requests blocked by rate limiter"
)