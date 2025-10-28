# ⚡ Crypto Matching Engine (Python, REG NMS–Inspired)

A high-performance cryptocurrency matching engine implementing **REG NMS–style price–time priority** and **internal order protection** — built in Python with FastAPI + async WebSocket feeds.  
Includes an optional **HTML dashboard** for live order-book visualization.

---

## ✨ Features

### 🔧 Core Matching Logic
- **Price–Time Priority (FIFO)** within each price level  
- **Internal Trade-Through Protection** — marketable orders sweep from best price outward  
- Supports all major order types:
  - 🟢 `market`
  - 🟡 `limit`
  - 🔵 `ioc` (Immediate-Or-Cancel)
  - 🔴 `fok` (Fill-Or-Kill)

### 🧩 Bonus Order Types
- ⛔ `stop_market` — activates as a market order when trigger hits  
- 🧱 `stop_limit` — activates as a limit order at a specified price  
- 🎯 `take_profit` — activates as a market order when price ≥ target  

### ⚙️ Engine Enhancements
- Real-time **BBO (Best Bid & Offer)** + **Top-10 Depth** feed via WebSocket  
- Real-time **Trade Execution** stream  
- **Maker–Taker fee model** (default 10 / 20 bps)  
- **Persistence:** order book state auto-save / reload (`/admin/save` / `/admin/load`)  
- **Async** FastAPI endpoints — fully event-loop safe  
- **Benchmarking utility** (`tests/benchmark_engine.py`)  
- Structured logging and unit tests  

---

## ⚙️ Quick Start

```bash
# 1️⃣ Create environment
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

# 2️⃣ Install dependencies
pip install -r requirements.txt

# 3️⃣ Run the engine API
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
📡 API Endpoints
🔹 Submit Order — POST /orders
Example Request

json
Copy code
{
  "symbol": "BTC-USDT",
  "order_type": "limit",
  "side": "buy",
  "quantity": "0.5",
  "price": "60000"
}
Example Response

json
Copy code
{
  "order_id": "f11c2460-de0b-46cc-9500-4f585ab36a9d",
  "resting": false,
  "trades": [
    {
      "trade_id": "c7281732-4207-4e3b-9cbe-7ffbc7e34042",
      "price": "60000",
      "quantity": "0.5",
      "aggressor_side": "buy"
    }
  ]
}
🔹 Market Data Feed — WS /ws/marketdata?symbol=BTC-USDT
Real-time Top-10 Depth updates.

json
Copy code
{
  "timestamp": "2025-10-24T04:41:51.774Z",
  "symbol": "BTC-USDT",
  "bids": [["59990", "2.5"], ["59980", "1.0"]],
  "asks": [["60010", "1.2"], ["60020", "0.8"]]
}
🔹 Trade Stream — WS /ws/trades?symbol=BTC-USDT
Trade execution feed.

json
Copy code
{
  "timestamp": "2025-10-24T04:41:51.774Z",
  "symbol": "BTC-USDT",
  "trade_id": "16ad2226-0e17-4ef3-8c1f-618b94df5446",
  "price": "60100",
  "quantity": "0.5",
  "aggressor_side": "buy",
  "maker_order_id": "cc56e375-0486-4349-bd79-aa7ce00490f8",
  "taker_order_id": "1471c8e2-c8f7-4a72-a2c2-53bed4f02c5a"
}
🧩 Example Test Scenarios
1️⃣ Limit + Market Fill
bash
Copy code
# Add resting ask
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"limit","side":"sell","quantity":"1","price":"60000"}'

# Cross with market buy
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"market","side":"buy","quantity":"1"}'
2️⃣ IOC Partial Fill
bash
Copy code
# Sell 0.5 available
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"limit","side":"sell","quantity":"0.5","price":"60100"}'

# IOC buy 2.0 — partial fill + cancel remainder
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"ioc","side":"buy","quantity":"2.0","price":"60100"}'
3️⃣ FOK All-or-Nothing
bash
Copy code
# Seed liquidity
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"limit","side":"sell","quantity":"2","price":"59990"}'
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"limit","side":"sell","quantity":"3","price":"60000"}'

# FOK buy 5.0 @60000 → fills all
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"fok","side":"buy","quantity":"5.0","price":"60000"}'
4️⃣ Stop & Take-Profit Triggers
bash
Copy code
# Stop-market sell triggers when price <= 59950
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"stop_market","side":"sell","quantity":"0.7","trigger_price":"59950"}'

# Take-profit sell triggers when price >= 60500
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"take_profit","side":"sell","quantity":"0.3","trigger_price":"60500"}'
5️⃣ Persistence (Save / Load)
bash
Copy code
# Save current order book
curl -X POST localhost:8000/admin/save?symbol=BTC-USDT

# Reload state after restart
curl -X POST localhost:8000/admin/load?symbol=BTC-USDT
6️⃣ Benchmark
bash
Copy code
python tests/benchmark_engine.py
# Output:
# Orders: 10000, Elapsed: 2.1s, Throughput: 4700 ord/s
# Latency (us): p50=110, p95=330, p99=700
🧠 Design Overview
📘 Order Book
Bid side → max-heap by price

Ask side → min-heap by price

Each price level stores a FIFO deque of orders

⚡ Matching Logic
Marketable orders sweep best-price first

FOK pre-validates liquidity before execution

IOC cancels any unfilled portion

Stop/TP activate on trigger conditions

Matching emits trade + market-data events asynchronously

💸 Fee Model
Maker: 0.10% (10 bps)

Taker: 0.20% (20 bps)

Fees shown in each trade payload:

json
Copy code
{ "maker_fee": "60.0000", "taker_fee": "120.0000" }
💾 Persistence
Saves order book and triggers to JSON (state/orderbook_<symbol>.json)

Restores cleanly after restart

🚀 Performance
O(log N) price access via heaps

Async broadcast queues for low latency

Benchmarked >1000 orders/sec on a single core

🌐 Frontend Dashboard (index.html)
A simple, dependency-free HTML dashboard to visualize:

🔹 Real-time order book (bids / asks)

🔹 Trade tape

🔹 Live BBO display

🔹 Order form supporting all types:

market, limit, ioc, fok

stop_market, stop_limit, take_profit

trigger_price input auto-appears when needed

Usage
1️⃣ Start backend:

bash
Copy code
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
2️⃣ Open index.html in your browser.
3️⃣ Set Base URL = http://127.0.0.1:8000 and click Connect Feeds.

🧱 Folder Structure
crypto-matching-engine/
├── app/
│   └── main.py              # FastAPI server (REST + WS)
├── engine/
│   ├── matching_engine.py   # Core matching logic (async)
│   ├── order_book.py        # Order book + heaps
│   ├── models.py            # Data models (Order, Trade)
│   └── __init__.py
├── tests/
│   ├── test_engine.py       # Unit tests
│   └── benchmark_engine.py  # Performance tests
├── state/                   # Persistence snapshots
├── index.html               # Simple frontend UI
└── requirements.txt

Frontend auto-connects WebSockets and dynamically shows relevant order fields.  
You can extend this engine with more order types, persistent queues, or multi-symbol support easily.  
Built with ❤️ for low-latency trading simulation and exchange research.

