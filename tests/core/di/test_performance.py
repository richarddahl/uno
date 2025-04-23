# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
import time

from uno.core.di.container import ServiceCollection


class FastService:
    def __init__(self):
        self.value = 123

class SlowService:
    def __init__(self):
        time.sleep(0.05)  # simulate slow construction
        self.value = 456

def test_resolution_path_caching_speed():
    services = ServiceCollection()
    services.add_singleton(FastService)
    resolver = services.build()
    r1 = resolver.resolve(FastService)
    r2 = resolver.resolve(FastService)
    from uno.core.errors.result import Success
    assert isinstance(r1, Success)
    assert isinstance(r2, Success)
    assert r1.value is r2.value  # Should always be the same singleton instance

def test_prewarm_singletons_eagerly_instantiates():
    services = ServiceCollection()
    services.add_singleton(SlowService)
    resolver = services.build()
    t0 = time.time()
    resolver.prewarm_singletons()
    t1 = time.time()
    # After prewarm, resolving should be fast (already constructed)
    t2 = time.time()
    resolver.resolve(SlowService)
    t3 = time.time()
    # Prewarm should take at least as long as construction
    assert (t1 - t0) > 0.04
    # Post-prewarm resolve should be very fast
    assert (t3 - t2) < 0.01
