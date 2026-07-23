"""Unit tests for the platform rate limiter."""

import threading

from modules.security.rate_limiter import RateLimiter


def test_allows_up_to_limit_then_refuses():
    rl = RateLimiter()
    results = [rl.allow("k", 3, 60)[0] for _ in range(5)]
    assert results == [True, True, True, False, False]


def test_refusals_do_not_extend_lockout():
    rl = RateLimiter()
    for _ in range(3):
        rl.allow("k", 3, 60)
    # Hammering while locked out must not add hits
    for _ in range(50):
        allowed, retry = rl.allow("k", 3, 60)
        assert not allowed
        assert retry >= 1


def test_window_expiry_restores_allowance(monkeypatch):
    import modules.security.rate_limiter as mod
    t = [1000.0]
    monkeypatch.setattr(mod.time, "monotonic", lambda: t[0])
    rl = RateLimiter()
    assert rl.allow("k", 2, 10)[0]
    assert rl.allow("k", 2, 10)[0]
    assert not rl.allow("k", 2, 10)[0]
    t[0] += 11  # window passes
    assert rl.allow("k", 2, 10)[0]


def test_keys_are_independent():
    rl = RateLimiter()
    assert rl.allow("a", 1, 60)[0]
    assert not rl.allow("a", 1, 60)[0]
    assert rl.allow("b", 1, 60)[0]


def test_reset_by_prefix():
    rl = RateLimiter()
    rl.allow("login|1.2.3.4", 1, 60)
    rl.allow("chat|user", 1, 60)
    rl.reset("login|")
    assert rl.allow("login|1.2.3.4", 1, 60)[0]
    assert not rl.allow("chat|user", 1, 60)[0]


def test_thread_safety_under_contention():
    rl = RateLimiter()
    allowed = []
    lock = threading.Lock()

    def worker():
        for _ in range(200):
            ok, _ = rl.allow("shared", 100, 60)
            if ok:
                with lock:
                    allowed.append(1)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert len(allowed) == 100  # exactly the limit, no lost updates
