from fastapi import FastAPI
from middleware.rate_limiter import RateLimiterMiddleware

app = FastAPI()

app.add_middleware(RateLimiterMiddleware)


@app.get("/")
def home():
    return {
        "message": "API Working"
    }