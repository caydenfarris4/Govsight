"""
In-process sliding-window rate limiter for the platform API.

Purpose-built for the two things that cost real money or invite abuse:
AI endpoints (per-request provider spend) and credential endpoints
(brute force). Keys are caller-scoped (username or client IP), windows
are sliding, and state is process-local - appropriate for the platform's
single-process deployment. If the API is ever scaled horizontally, move
the counters to a shared store; the interface stays the same.
"""

import threading
import time
from collections import defaultdict, deque
from typing import Tuple

_MAX_TRACKED_KEYS = 50_000  # memory bound; hit only under distributed abuse


class RateLimiter:
    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_s: float) -> Tuple[bool, int]:
        """Record one hit for `key`; return (allowed, retry_after_seconds).

        Sliding window: at most `limit` hits within any `window_s` span.
        The hit is only recorded when allowed, so refused requests do not
        extend the caller's own lockout.
        """
        now = time.monotonic()
        with self._lock:
            if len(self._hits) > _MAX_TRACKED_KEYS:
                # Bound memory under key-churn abuse; forgiving reset is
                # preferable to unbounded growth.
                self._hits.clear()
            dq = self._hits[key]
            cutoff = now - window_s
            while dq and dq[0] <= cutoff:
                dq.popleft()
            if len(dq) >= limit:
                retry_after = max(1, int(dq[0] + window_s - now) + 1)
                return False, retry_after
            dq.append(now)
            return True, 0

    def reset(self, key_prefix: str = "") -> None:
        """Clear tracked hits (all, or those whose key starts with prefix)."""
        with self._lock:
            if not key_prefix:
                self._hits.clear()
                return
            for k in [k for k in self._hits if k.startswith(key_prefix)]:
                del self._hits[k]


# Shared instance for the API process
rate_limiter = RateLimiter()
