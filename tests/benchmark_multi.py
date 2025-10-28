# import time
# from decimal import Decimal
# from statistics import median
# from engine.matching_engine import MatchingEngine
# from engine.models import Order

# SYM = "BTC-USDT"

# def mk(side, qty, px=None, t="limit"):
#     return Order(symbol=SYM, order_type=t, side=side,
#                  quantity=Decimal(str(qty)),
#                  price=Decimal(str(px)) if px is not None else None)

# def run_once(n):
#     eng = MatchingEngine()
#     for i in range(1000):
#         eng.submit(mk("sell", 0.01, 60000 + (i % 50)))
#         eng.submit(mk("buy",  0.01, 59950 - (i % 50)))
#     lat = []
#     t0 = time.perf_counter()
#     for i in range(n):
#         o = mk("buy", 0.005, 60010, "ioc") if i % 2 == 0 else mk("sell", 0.005, 59990, "ioc")
#         s = time.perf_counter()
#         eng.submit(o)
#         lat.append((time.perf_counter() - s) * 1e6)  # microseconds
#     dt = time.perf_counter() - t0
#     lat.sort()
#     return {
#         "N": n,
#         "elapsed_s": dt,
#         "throughput_ops": n/dt,
#         "p50_us": lat[int(0.50*len(lat))],
#         "p95_us": lat[int(0.95*len(lat))],
#         "p99_us": lat[int(0.99*len(lat))]
#     }

# if __name__ == "__main__":
#     for n in (5_000, 10_000, 20_000):
#         r = run_once(n)
#         print(f"N={r['N']:,}  elapsed={r['elapsed_s']:.2f}s  thr={r['throughput_ops']:.0f}/s  p50={r['p50_us']:.0f}us  p95={r['p95_us']:.0f}us  p99={r['p99_us']:.0f}us")
# tests/benchmark_multi.py
import asyncio
import time
from decimal import Decimal
from typing import Dict, Any
from engine.matching_engine import MatchingEngine
from engine.models import Order

SYM = "BTC-USDT"

def mk(side, qty, px=None, t="limit") -> Order:
    return Order(
        symbol=SYM,
        order_type=t,
        side=side,
        quantity=Decimal(str(qty)),
        price=Decimal(str(px)) if px is not None else None,
    )

async def run_once(n: int) -> Dict[str, Any]:
    eng = MatchingEngine()

    # Seed both sides
    for i in range(1000):
        await eng.submit(mk("sell", 0.01, 60000 + (i % 50)))
        await eng.submit(mk("buy",  0.01, 59950 - (i % 50)))

    lat_us = []
    t0 = time.perf_counter()
    for i in range(n):
        o = mk("buy", 0.005, 60010, "ioc") if (i % 2 == 0) else mk("sell", 0.005, 59990, "ioc")
        s = time.perf_counter()
        await eng.submit(o)
        lat_us.append((time.perf_counter() - s) * 1e6)
    dt = time.perf_counter() - t0

    lat_us.sort()
    def pct(p): return lat_us[int(p * len(lat_us))]

    return {
        "N": n,
        "elapsed_s": dt,
        "throughput_ops": n / dt,
        "p50_us": pct(0.50),
        "p95_us": pct(0.95),
        "p99_us": pct(0.99),
    }

async def main():
    for n in (5_000, 10_000, 20_000):
        r = await run_once(n)
        print(f"N={r['N']:,}  elapsed={r['elapsed_s']:.2f}s  thr={r['throughput_ops']:.0f}/s  "
              f"p50={r['p50_us']:.0f}us  p95={r['p95_us']:.0f}us  p99={r['p99_us']:.0f}us")

if __name__ == "__main__":
    asyncio.run(main())
