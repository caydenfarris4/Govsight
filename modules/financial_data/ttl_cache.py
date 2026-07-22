"""
Small time-aware cache decorator for market-data connectors.

functools.lru_cache never expires within a process, which let investment
rates go stale for the lifetime of the server. This decorator caches per
argument set with a TTL, so rates refresh on a schedule while repeated
renders within the window stay fast.
"""

import time
from functools import wraps
from threading import Lock
from typing import Any, Callable, Dict, Tuple


def ttl_cache(ttl_seconds: int = 900, maxsize: int = 64):
    def decorator(fn: Callable) -> Callable:
        cache: Dict[Tuple, Tuple[float, Any]] = {}
        lock = Lock()

        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            with lock:
                hit = cache.get(key)
                if hit is not None and now - hit[0] < ttl_seconds:
                    return hit[1]
            value = fn(*args, **kwargs)
            with lock:
                if len(cache) >= maxsize:
                    oldest = min(cache, key=lambda k: cache[k][0])
                    del cache[oldest]
                cache[key] = (now, value)
            return value

        def cache_clear():
            with lock:
                cache.clear()

        wrapper.cache_clear = cache_clear
        return wrapper
    return decorator
