# 🎯 Bonus Features & Optimizations

## Advanced Order Types
### stop_market
- **Trigger:** fires when adverse price passes `trigger_price`  
- **Child:** `market` order  
- **Rationale:** risk protection (stop-loss)

### stop_limit
- **Trigger:** fires at `trigger_price`  
- **Child:** `limit` order at `price` (or `trigger_price` if `price` omitted)  
- **Rationale:** controlled exit without slippage beyond limit

### take_profit
- **Trigger:** fires when favorable price hits `trigger_price`  
- **Child:** `market` order  
- **Rationale:** secure profits at targets

## Persistence
- **Save:** `POST /admin/save?symbol=BTC-USDT` → `state/orderbook_BTC-USDT.json`  
- **Load:** `POST /admin/load?symbol=BTC-USDT`  
- **Scope:** restores resting orders and trigger orders

## Fee Model
- Default: **Maker 10 bps**, **Taker 20 bps**  
- Included in trade payloads: `maker_fee`, `taker_fee`  
- Configurable in `MatchingEngine(maker_fee_bps=..., taker_fee_bps=...)`

## Concurrency & Stability
- Per-symbol **async lock** around matching
- WS market data & trade streams **fan-out** via async queues
- Engine methods are **async** to avoid nested event loop issues

## Performance Notes
- O(log N) best-price + FIFO at level → predictable latency
- Benchmarked with `tests/benchmark_engine.py`
- See **PERFORMANCE.md** for results and suggestions
