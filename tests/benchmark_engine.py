# tests/benchmark_engine.py
import time, random
from decimal import Decimal
from engine.matching_engine import MatchingEngine
from engine.models import Order

SYM = "BTC-USDT"

def mk(side, qty, px=None, t="limit"):
    return Order(symbol=SYM, order_type=t, side=side, quantity=Decimal(str(qty)), price=Decimal(str(px)) if px else None)

def run_benchmark(n=10_000):
    eng = MatchingEngine()
    # Seed both sides
    for i in range(1000):
        eng.submit(mk("sell", qty=0.01, px=60000 + (i % 50)))
        eng.submit(mk("buy", qty=0.01, px=59950 - (i % 50)))
    # Run
    t0 = time.perf_counter()
    lat = []
    for i in range(n):
        if i % 2 == 0:
            o = mk("buy", qty=0.005, px=60010, t="ioc")
        else:
            o = mk("sell", qty=0.005, px=59990, t="ioc")
        s = time.perf_counter()
        eng.submit(o)
        lat.append((time.perf_counter() - s)*1e6)  # us
    dt = time.perf_counter() - t0
    tps = n/dt
    lat.sort()
    p50 = lat[int(0.5*len(lat))]
    p95 = lat[int(0.95*len(lat))]
    p99 = lat[int(0.99*len(lat))]
    print(f"Orders: {n}, Elapsed: {dt:.3f}s, Throughput: {tps:,.0f} ord/s")
    print(f"Latency (us): p50={p50:.0f}, p95={p95:.0f}, p99={p99:.0f}")

if __name__ == "__main__":
    run_benchmark()
