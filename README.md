# ⚡ Crypto Matching Engine (Python, REG NMS–Inspired)

A high-performance cryptocurrency matching engine implementing **REG NMS–style price–time priority** and **internal order protection** — built in **Python** using **FastAPI** and **async WebSocket feeds**.  
Includes an optional **HTML dashboard frontend** for real-time visualization of the order book, trades, and BBO (Best Bid & Offer).

---

## ✨ Features

### 🔧 Core Matching Logic
- **Price–Time Priority (FIFO)** within each price level  
- **Internal Trade-Through Protection** — marketable orders always match best available prices before crossing the book  
- Supports major order types:
  - 🟢 `market`
  - 🟡 `limit`
  - 🔵 `ioc` (Immediate-Or-Cancel)
  - 🔴 `fok` (Fill-Or-Kill)

### 🧩 Bonus Order Types
- ⛔ `stop_market` — activates as a market order when trigger price is reached  
- 🧱 `stop_limit` — activates as a limit order at a specified trigger price  
- 🎯 `take_profit` — activates as a market order when the market reaches a target price  

### ⚙️ Engine Enhancements
- Real-time **BBO (Best Bid & Offer)** + **Top-10 Depth** feed via WebSocket  
- Real-time **Trade Execution** stream  
- **Maker–Taker fee model** (default: 10 / 20 bps)  
- **Persistence** — order book state can auto-save/reload (`/admin/save`, `/admin/load`)  
- Fully **async** and event-loop safe (no blocking or nested loop errors)  
- Built-in **benchmarking** utility (`tests/benchmark_engine.py`)  
- Structured logging and **unit test coverage**  

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
Real-time Top-10 depth updates.

json
Copy code
{
  "timestamp": "2025-10-24T04:41:51.774Z",
  "symbol": "BTC-USDT",
  "bids": [["59990", "2.5"], ["59980", "1.0"]],
  "asks": [["60010", "1.2"], ["60020", "0.8"]]
}
🔹 Trade Stream — WS /ws/trades?symbol=BTC-USDT
Real-time trade execution feed.

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
Bid side → max-heap (best price highest)

Ask side → min-heap (best price lowest)

Each price level stores a FIFO deque of orders

Enables O(log N) access for best price and O(1) queue management

⚡ Matching Logic
Marketable orders sweep from best price outward

FOK: pre-validates full quantity before execution

IOC: executes partial fills, cancels remainder

Stop/Take-Profit: activate once trigger met

Matching emits trade + market data updates asynchronously

💸 Fee Model
Maker: 0.10% (10 bps)

Taker: 0.20% (20 bps)

Fees shown in trade payload:

json
Copy code
{ "maker_fee": "60.0000", "taker_fee": "120.0000" }
💾 Persistence
Saves state → state/orderbook_<symbol>.json

Restores cleanly on restart for replayable trading sessions

🚀 Performance
O(log N) best-price lookup via heaps

Async I/O for non-blocking WebSocket fan-out

Benchmarked >1000 orders/sec on a single core

🌐 Frontend Dashboard (index.html)
A minimal, dependency-free web UI for testing and monitoring.

Displays

Real-time order book (bids / asks)

Trade tape

BBO values

Order form supporting all order types
(market, limit, ioc, fok, stop_market, stop_limit, take_profit)

Usage

bash
Copy code
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
Then open index.html and set:

java
Copy code
Base URL = http://127.0.0.1:8000
Click Connect Feeds to view real-time updates.

🧱 Folder Structure
perl
Copy code
crypto-matching-engine/
├── app/
│   └── main.py              # FastAPI server (REST + WebSocket)
├── engine/
│   ├── matching_engine.py   # Core matching logic
│   ├── order_book.py        # Order book structures
│   ├── models.py            # Order, Trade, Trigger classes
│   └── __init__.py
├── tests/
│   ├── test_engine.py       # Unit tests
│   └── benchmark_engine.py  # Performance benchmark
├── state/                   # Order book persistence files
├── index.html               # Frontend dashboard
└── requirements.txt

🧩 Requirements
makefile
Copy code
fastapi==0.115.2
uvicorn[standard]
pydantic==2.9.2
orjson==3.10.7
pytest==8.3.3
websockets==12.0
🧱 System Architecture & Design Decisions
🧩 Architecture Overview
css
Copy code
[Frontend (index.html)]
     │
     ▼
(REST API / WebSocket Layer)
     │
     ▼
[FastAPI Application]
     │
     ▼
[Matching Engine Core]
 ├─ OrderBook (Heaps + FIFO)
 ├─ MatchingEngine (Price–Time + Triggers)
 ├─ FeeModel / Trade Generator
 ├─ Async Channels (MarketData, Trades)
 └─ JSON Persistence (state/)
Frontend → Sends REST orders & listens to WebSocket feeds.

FastAPI Layer → Handles requests asynchronously, forwards to the engine.

Matching Engine Core → Executes all business logic and maintains state.

Persistence Layer → Provides fault recovery and replay.

Broadcast Channels → Enable low-latency market/trade updates to all clients.

🔹 Key Design Decisions
Design Element	Rationale
Python + FastAPI + asyncio	Simple async model and easy JSON serialization for rapid prototyping.
Heaps (price) + Deques (FIFO)	Achieves O(log N) for price lookup and O(1) for queue order.
Async event loop	Non-blocking execution for simultaneous REST and WS traffic.
In-memory state + JSON persistence	Lightweight and transparent vs. database overhead.
Broadcast queues for WebSocket	Low latency fan-out and easy scalability to multiple clients.
Maker–Taker fee model	Emulates real exchange economics.
Stop/Take-Profit triggers	Expands to realistic order management scenarios.

⚖️ Trade-Off Decisions
Area	Decision	Trade-Off
Language Choice	Python (FastAPI) for clarity and async support	Lower raw performance than C++ but faster iteration speed
Data Persistence	JSON files instead of SQL/Redis	Easier to debug; not ideal for very high-frequency data
Single-threaded Async Model	Simple and deterministic	Limited CPU scaling without multiprocessing
Heaps + Deques	Efficient and intuitive structure	Harder to handle partial level aggregation
In-memory Engine	Ultra-fast access for demo / local tests	Needs persistence for production-grade fault tolerance

🧩 Summary
This system provides:

Exchange-grade matching logic (price–time priority + FIFO)

Conditional orders and fees like real trading venues

Real-time market data streaming via WebSockets

Modular and extendable design — easy to scale into a production microservice

Built with ❤️ for low-latency trading simulation, research, and exchange prototyping.