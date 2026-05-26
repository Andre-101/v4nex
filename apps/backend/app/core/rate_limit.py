from dataclasses import dataclass
from time import monotonic

from app.core.config import settings
from app.core.errors import AppError, ErrorCode


@dataclass
class RateLimitBucket:
    window_started_at: float
    count: int


_buckets: dict[str, RateLimitBucket] = {}


def clear_rate_limits() -> None:
    _buckets.clear()


def check_rate_limit(
    operation: str,
    key: str,
    *,
    max_requests: int | None = None,
    window_seconds: int | None = None,
) -> None:
    if not settings.rate_limit_enabled:
        return

    limit = max_requests or settings.rate_limit_max_requests
    window = window_seconds or settings.rate_limit_window_seconds
    now = monotonic()
    bucket_key = f"{operation}:{key}"
    bucket = _buckets.get(bucket_key)

    if bucket is None or now - bucket.window_started_at >= window:
        _buckets[bucket_key] = RateLimitBucket(window_started_at=now, count=1)
        return

    bucket.count += 1
    if bucket.count > limit:
        raise AppError(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message="Rate limit exceeded. Please retry later.",
            details={"operation": operation},
        )
